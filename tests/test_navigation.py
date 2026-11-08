from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

from app.benefits import cash_cost, clean_plan, comparison, insured_cost, number
from app.catalog import candidates
from app.config import Config
from app.egress import Egress, EgressBlocked, dlp_violations
from app.navigation import clean_input, ranked, update_quote
from app.server import App
from app.store import Store, VaultError


def person(**changes):
    return dict(city="Boston", state="MA", zip="", insurance="no", wants_insurance=True,
                service="primary_care", visit_date=date.today().isoformat(), language="Chinese",
                priority="balanced", budget=200, months=1, adult=True, routine_confirmed=True,
                description="Private test concern", history="Private test history", medications="Synthetic Med One",
                demo=True, plan=plan(), **changes)


def plan(**changes):
    base = dict(name="Demo Student PPO", rule="deductible", start=date.today().isoformat(), end="",
                premium=95, copay=25, deductible_remaining=50, coinsurance=20, oop_remaining=3000, eligible=False)
    base.update(changes)
    return base


class CostTests(unittest.TestCase):
    def setUp(self):
        self.provider = candidates("Boston", "MA", True)[0]
        self.provider["coverage"]["Demo Student PPO"]["allowed_amount"] = 200
        self.day = date.today().isoformat()

    def estimate(self, **changes):
        return insured_cost(self.provider, plan(**changes), self.day, "primary_care")

    def test_deductible_then_coinsurance(self):
        self.assertEqual(self.estimate()["amount"], 80)

    def test_oop_cap(self):
        self.assertEqual(self.estimate(oop_remaining=30)["amount"], 30)

    def test_zero_is_valid_not_unknown(self):
        self.assertEqual(self.estimate(oop_remaining=0)["amount"], 0)
        self.assertIsNone(self.estimate(oop_remaining=None)["amount"])

    def test_copay_rule_does_not_add_deductible(self):
        self.assertEqual(self.estimate(rule="copay")["amount"], 25)

    def test_unknown_and_out_of_network_not_zero(self):
        self.provider["coverage"] = {}
        self.assertIsNone(self.estimate()["amount"])

    def test_service_scope_is_required(self):
        self.assertIsNone(insured_cost(self.provider, plan(), self.day, "follow_up")["amount"])
        self.assertIsNone(cash_cost(self.provider, "follow_up")["amount"])

    def test_future_coverage_cannot_pay_today(self):
        out = self.estimate(start=(date.today()+timedelta(days=20)).isoformat())
        self.assertEqual(out["status"], "not_active")
        self.assertIsNone(out["amount"])

    def test_expired_coverage(self):
        self.assertIsNone(self.estimate(end=(date.today()-timedelta(days=1)).isoformat())["amount"])

    def test_stale_network_price_needs_reconfirmation(self):
        self.provider["coverage"]["Demo Student PPO"]["checked_on"]=(date.today()-timedelta(days=31)).isoformat()
        self.assertIsNone(self.estimate()["amount"])

    def test_include_premiums_and_negative_savings(self):
        c=comparison(self.provider, plan(), self.day,"primary_care",1)
        self.assertEqual(c["visit_difference"],40)
        self.assertEqual(c["total_with_plan"],175)
        self.assertEqual(c["net_difference"],-55)
        self.assertFalse(c["eligible"])

    def test_missing_premium_cannot_claim_net_savings(self):
        c=comparison(self.provider,plan(premium=None),self.day,"primary_care")
        self.assertIsNone(c["net_difference"])

    def test_numeric_validation_rejects_nonfinite_negative_and_boolean(self):
        for value in ("nan", "Infinity", -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                number(value,"Cost")


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        cfg=Config();cfg.store_path=Path(self.tmp.name)/"vault.fv";cfg.exa_key="";cfg.tavily_key=""
        self.app=App(cfg)
        self.call("/api/vault/create", {"passphrase":"disposable-test-passphrase"})

    def tearDown(self):
        self.tmp.cleanup()

    def call(self,path,body=None,query=None):
        return self.app.dispatch("GET" if body is None else "POST",path,body or {},query or {})

    def search(self,p=None):
        preview=self.call("/api/preview",p or person())
        return self.call("/api/search",dict(token=preview["token"],approved=True,live=False))

    def test_uninsured_branch_and_persistent_encryption(self):
        result=self.search()
        self.assertEqual(result["results"][0]["provider"]["id"],"harbor")
        self.assertEqual(result["results"][0]["pathway"],"Self-pay")
        raw=self.app.store.path.read_bytes()
        self.assertNotIn(b"Private test concern",raw)
        ident=result["id"]
        self.call("/api/vault/lock",{})
        with self.assertRaises(VaultError):self.call("/api/case",query={"id":[ident]})
        self.call("/api/vault/unlock",{"passphrase":"disposable-test-passphrase"})
        self.assertEqual(self.call("/api/case",query={"id":[ident]})["input"]["description"],"Private test concern")

    def test_insured_branch_uses_lower_supported_share(self):
        p=person();p["insurance"]="yes";p["plan"]=plan(rule="copay")
        result=self.search(p)
        self.assertTrue(all(r["cost"]["amount"]==25 for r in result["results"]))
        self.assertTrue(all(r["pathway"]=="Your insurance" for r in result["results"]))

    def test_priority_change_reorders_same_providers(self):
        result=self.search()
        cost=self.call("/api/case/preferences",{"id":result["id"],"priority":"cost"})
        self.assertEqual(cost["results"][0]["provider"]["id"],"maple")
        rating=self.call("/api/case/preferences",{"id":result["id"],"priority":"rating"})
        self.assertEqual(rating["results"][0]["provider"]["id"],"park")

    def test_real_data_is_not_given_synthetic_prices(self):
        p=person();p["demo"]=False;p["plan"]=None
        result=self.search(p)
        self.assertGreater(len(result["results"]),0)
        self.assertTrue(all(r["cost"]["amount"] is None and r["provider"]["rating"] is None for r in result["results"]))

    def test_other_city_has_no_boston_substitution(self):
        p=person();p.update(city="Denver",state="CO",demo=False)
        self.assertEqual(self.search(p)["results"],[])

    def test_unapproved_and_reused_preview_refused(self):
        token=self.call("/api/preview",person())["token"]
        with self.assertRaises(ValueError):self.call("/api/search",{"token":token,"approved":False})
        with self.assertRaises(ValueError):self.call("/api/search",{"token":token,"approved":True})

    def test_unknown_medical_goal_not_triaged_by_price(self):
        p=person();p["routine_confirmed"]=False
        with self.assertRaises(ValueError):self.call("/api/preview",p)

    def test_quote_updates_only_matching_plan_and_service(self):
        p=person();p.update(demo=False,insurance="yes",plan=plan(name="Actual entered plan",rule="copay"))
        result=self.search(p)
        result=self.call("/api/case/quote",dict(id=result["id"],provider_id="fenway",checked_on=date.today().isoformat(),
                source="Test billing office call",cash=110,plan_name="Actual entered plan",scope_confirmed=True,
                network_confirmed=True,service_confirmed=True))
        fenway=next(r for r in result["results"] if r["provider"]["id"]=="fenway")
        self.assertEqual(fenway["cost"]["amount"],25)
        self.assertEqual(fenway["cost"]["status"],"conditional")
        other=self.call("/api/case/preferences",dict(id=result["id"],plan=plan(name="Another plan")))
        self.assertTrue(all(r["insured"]["amount"] is None for r in other["results"]))

    def test_invalid_quote_is_atomic(self):
        result=self.search()
        old=deepcopy(self.app.get_case(result["id"])["providers"])
        with self.assertRaises(ValueError):
            self.call("/api/case/quote",dict(id=result["id"],provider_id="harbor",checked_on=date.today().isoformat(),
                    source="test",cash=1,scope_confirmed=True,rating=5,rating_count=10,rating_source="javascript:bad"))
        self.assertEqual(self.app.get_case(result["id"])["providers"],old)

    def test_booking_needs_confirmation(self):
        result=self.search()
        with self.assertRaises(ValueError):self.call("/api/case/contact",dict(id=result["id"],status="booked"))
        saved=self.call("/api/case/contact",dict(id=result["id"],status="booked",provider_id=result["providers"][0]["id"],reference="User called, confirmed 9am"))
        self.assertEqual(saved["status"],"booked")


class PrivacyTests(unittest.TestCase):
    def test_encoded_private_data_and_headers_blocked(self):
        data={"profile":{"member_id":"ABC123456"},"cases":{},"bills":{}}
        for payload in ({"url":"https://example.com/ABC%2531%2532%2533456"},
                        {"headers":{"x-note":"ABC123456"}}, {"ABC123456":"irrelevant"}):
            with self.subTest(payload=payload):
                self.assertIn("member_id",dlp_violations(payload,data,["ABC123456"]))

    def test_local_model_refuses_remote_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Config();store=Store(Path(d)/"v");guard=Egress(store,cfg)
            with self.assertRaises(EgressBlocked):guard.local("GET","https://model.example/api/tags")

    def test_offline_blocks_before_sending(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=Config();store=Store(Path(d)/"v");store.create("test-passphrase")
            guard=Egress(store,cfg);guard.offline=True
            with self.assertRaises(EgressBlocked):guard.http("POST",cfg.exa_base+"/search",service="Exa",purpose="test")
            self.assertEqual(store.data["ledger"][-1]["status"],"blocked")


if __name__=="__main__":unittest.main()
