"""Provider sources: FirstVisit decides what to search; the source turns it into results."""
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

from app.config import Config
from app.server import App
from app.sources import ZocdocLink, describe_all
from tests.test_person_first import health_first

NEU = {"name": "Northeastern University Student Health Plan - Blue Care Elect PPO", "rule": "copay", "zocdoc_product": "bcbsma_blue_care_elect_ppo"}


def q(person):
    d = ZocdocLink().describe(person)
    return d, {k: v[0] for k, v in parse_qs(urlparse(d["url"]).query, keep_blank_values=True).items()}


class LinkTests(unittest.TestCase):
    def test_urgent_care_in_network_for_neu_plan(self):
        d, p = q({"service": "same_day", "zip": "02115", "insurance": "yes", "plan": NEU})
        self.assertTrue(d["url"].startswith("https://www.zocdoc.com/search?"))
        self.assertEqual((p["dr_specialty"], p["reason_visit"]), ("513", "1542"))
        self.assertEqual((p["insurance_carrier"], p["insurance_plan"]), ("573", "31215"))
        self.assertEqual(p["address"], "02115")
        self.assertTrue(d["in_network_filter"])

    def test_name_alone_never_selects_product(self):
        for name in (NEU["name"], "Not Blue Care Elect", "Other State Blue Care Elect PPO"):
            d, params = q({"insurance": "yes", "plan": {"name": name}})
            self.assertFalse(d["in_network_filter"])
            self.assertEqual(params["insurance_plan"], "-1")

    def test_explicit_product_survives_plan_validation(self):
        from app.benefits import clean_plan
        plan = clean_plan(NEU)
        self.assertTrue(q({"insurance": "yes", "plan": plan})[0]["in_network_filter"])
        with self.assertRaises(ValueError):
            clean_plan(dict(NEU, zocdoc_product="invented"))

    def test_visit_kinds(self):
        self.assertEqual(q({"service": "primary_care", "need": "checkup", "zip": "02115"})[1]["reason_visit"], "76")
        self.assertEqual(q({"service": "follow_up", "zip": "02115"})[1]["reason_visit"], "1309")
        self.assertEqual(q({"service": "primary_care", "zip": "02115"})[1]["reason_visit"], "75")

    def test_unknown_plan_and_no_insurance_never_guess_ids(self):
        d, p = q({"service": "primary_care", "zip": "02115", "insurance": "yes", "plan": {"name": "Some Other PPO"}})
        self.assertEqual((p["insurance_carrier"], p["insurance_plan"]), ("", "-1"))
        self.assertFalse(d["in_network_filter"])
        d, p = q({"service": "primary_care", "city": "Boston", "state": "MA", "insurance": "no"})
        self.assertEqual(p["address"], "Boston, MA")
        self.assertIn("self-pay", d["note"])

    def test_link_never_carries_health_details(self):
        person = {"service": "same_day", "zip": "02115", "insurance": "yes", "plan": NEU,
                  "description": "eye infection", "history": "Asthma", "medications": "Inhaler", "age": 28}
        url = ZocdocLink().describe(person)["url"].lower()
        for private in ("eye", "asthma", "inhaler", "28"):
            self.assertNotIn(private, url.replace("02115", ""))

    def test_results_include_source(self):
        tmp = tempfile.TemporaryDirectory()
        cfg = Config(); cfg.store_path = Path(tmp.name) / "v.fv"; cfg.exa_key = ""; cfg.tavily_key = ""
        app = App(cfg)
        app.dispatch("POST", "/api/vault/create", {"passphrase": "disposable-test-passphrase"}, {})
        token = app.dispatch("POST", "/api/preview", health_first(zip="02115"), {})["token"]
        case = app.dispatch("POST", "/api/search", {"token": token, "approved": True, "live": False}, {})
        self.assertEqual(case["sources"][0]["source"], "Zocdoc")
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()


class DirectorySearchTests(unittest.TestCase):
    def test_name_and_address_lookup_is_local_and_sourced(self):
        from app.catalog import directory_search
        hits = directory_search('Dr. Hwang')
        self.assertEqual(hits[0]['type'], 'clinician'); self.assertIn('1180 Beacon', hits[0]['address']); self.assertTrue(hits[0]['url'].startswith('https://'))
        self.assertTrue(any(h['id'] == 'bwh-brookline' for h in directory_search('brookline place')))
        self.assertEqual(directory_search('dr'), []); self.assertEqual(directory_search('zzzz nobody'), [])

    def test_expanded_directory_is_sourced_and_honest(self):
        from app.catalog import directory_search, REAL, BROOKLINE, CLINICIANS, candidates
        self.assertTrue(any(h['id'] == 'bidmc-hca' for h in directory_search('Healthcare Associates')))
        self.assertTrue(any(h['id'] == 'nu-uhcs' for h in directory_search('Northeastern')))
        self.assertEqual(directory_search('Berz')[0]['type'], 'clinician')
        ids = {p['id'] for p in REAL + BROOKLINE}
        self.assertEqual(len(ids), len(REAL + BROOKLINE))
        for e in REAL + BROOKLINE + CLINICIANS:
            self.assertTrue(e['url'].startswith('https://'), e['id'])
            self.assertTrue(e.get('booking_url', 'https://').startswith('https://'), e['id'])
            self.assertRegex(e['source_note'], r'(?i)unconfirmed|confirm', e['id'])
        for c in CLINICIANS:
            self.assertIn(c['practice_id'], ids)
        self.assertTrue(all(p['city'] == 'Brookline' for p in candidates('Brookline', 'MA')))
        self.assertTrue(any(p['id'] == 'bmc-adult-pc' for p in candidates('Boston', 'MA')))
