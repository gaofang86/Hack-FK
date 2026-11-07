# FirstVisit

A local healthcare-navigation prototype for international students in Boston. Choose a location, tell the app whether you have insurance, add optional private context, and compare care options by personal cost, language, patient reviews, and known distance.

The first supported visit types are adult primary-care appointments and primary-care follow-ups. This is a functioning prototype, not a clinically validated triage system or a live insurance marketplace.

## Start

```sh
git clone https://github.com/gaofang86/Hack-FK.git
cd Hack-FK
python3 -m pip install -r requirements.txt
python3 run.py
```

Open http://127.0.0.1:8766. The server binds only to loopback. Choose your own vault passphrase at the review step. No account is created with an external service. The passphrase has no recovery mechanism. Do not commit the vault or `.env` file.

To use a temporary, unlocked test workspace instead:

```sh
python3 run.py --preview
```

Open http://127.0.0.1:8767. This uses a disposable vault, disables public search credentials, and displays a test banner. Use only synthetic information. If it locks, the test-only passphrase is `firstvisit-preview-only`. Normal startup does not use this passphrase or this vault.

## Actual user flow

1. Enter city/state and optional ZIP. Device coordinates are optional and stay local; they are never sent for geocoding.
2. Choose whether you already have insurance.
   - Yes: enter the exact plan and known service benefits.
   - No: continue with self-pay, or enter a plan to explore buying coverage.
3. Choose the known visit type, date, language, budget and ranking preference. Optional concerns/history/medications remain local. This version asks the user to confirm adult, non-emergency outpatient care; it does not infer urgency from absence of symptoms.
4. Create/unlock the encrypted vault. Review the exact public queries and recipients. Choose live discovery when configured, or the local directory only.
5. Compare source-labeled results. Missing prices, review ratings, service availability and network status stay unknown.
6. Add a scoped quote and exact-plan network confirmation for a specific provider/location/service. The app labels these user-entered and recalculates.
7. Compare the same visit under self-pay and an entered insurance plan, including the selected number of premium payments. A negative saving appears as a higher cost.
8. Prepare a call script locally; optionally use Ollama for a personalized draft. Visit the source/booking site yourself. Record the confirmation and next steps in the care journey.
9. Lock the vault or let the inactivity timer lock it. Resume through My care journeys after unlocking.

## What is real, manual, and synthetic

| Capability | Current implementation |
| --- | --- |
| Intake, branch navigation and preferences | Working local UI and API |
| Persistence | AES-256-GCM vault, scrypt key derivation, restrictive file permissions, lock and inactivity timeout |
| Boston directory | Small sourced directory with official links; no invented real prices, ratings, availability or networks |
| Live public discovery | Tavily and/or Exa adapter; requires your own API key; results are leads needing confirmation |
| Personal prices | Deterministic copay or deductible/coinsurance calculation using entered benefits and provider-specific evidence |
| Price / network evidence | User-confirmed quotes; source, date, service and plan attached |
| Reviews | Unknown unless supplied with a source URL/count; demo ratings are synthetic |
| Distance | Straight-line distance only when both coordinates exist; demo provider coordinates are synthetic |
| Local model | Ollama adapter; explicitly labeled built-in template when unavailable; no cloud fallback |
| Booking | Preparation and external handoff, followed by user-recorded confirmation; no automatic booking |
| Fictional example | Separate mode with four fictional Boston providers and a fictional plan; visible labels throughout |

An insurance card/SBC alone is not enough to establish a personal total. For deductible-based calculations, enter the applicable allowed amount, current remaining deductible, coinsurance, and remaining out-of-pocket limit. For the copay rule, confirm that the deductible does not apply to this service. Both require service-scoped network evidence. Network/price evidence older than 30 days relative to the visit date requires reconfirmation in this prototype; this is a product freshness policy, not a guarantee.

New-plan comparisons include ONE specified visit plus N premium payments. They are not a whole-year care forecast, do not infer subsidies or eligibility, and do not model family benefits, coordination of benefits, out-of-network balance billing, deductible-then-copay plans, extra tests, or benefit-year changes. Visits before coverage starts or after an entered end date do not receive an insured estimate. Plans with unsupported benefit structures need manual review.

For an existing insured person, the shortlist compares visit-level cash and insured shares. Choosing cash can affect deductible credit; ask the plan. The premium-inclusive panel is a separate scenario, not advice to cancel existing coverage.

## Connect services

Copy `.env.example` to `.env` and add either `TAVILY_API_KEY` or `EXA_API_KEY`. Restart the server. Public queries use only city/state/ZIP and a general primary-care category, disclosed before sending. The local ranking engine uses private information after discovery.

Install Ollama from its official distribution, then pull the configured model:

```sh
ollama pull qwen2.5:3b
```

Ollama must be running at the loopback URL in `.env`. The default model is small for a laptop; the presence of a local model does not establish medical competence. Its connected task drafts visit preparation, without deciding clinical appropriateness, prices or network status. Review model text before sharing.

## Public plan data strategy

Use official plan-year documents and confirmed member details, with source and effective dates. Do not infer a new year's benefits from an old PDF. This build links to:

- [Northeastern student plan and benefits](https://studenthealthplan.northeastern.edu/)
- [Massachusetts Health Connector plan comparison](https://betterhealthconnector.com/compare-plans)
- [Health Connector provider directory](https://providerdirectory.mahealthconnector.org/)
- [How total health costs work](https://www.healthcare.gov/choose-a-plan/your-total-costs/)

Zocdoc is useful for finding providers, and offers [verification for selected plans](https://www.zocdoc.com/patient-help/en/articles/16557288-what-is-the-in-network-promise). Scraping public provider pages does not provide that member verification or a personalized premium quote. No Zocdoc scraper, insurer enrollment API, or licensed review feed is included. Public-provider discovery and plan-benefit ingestion should remain separate integrations.

## Privacy scope

External app requests pass through `app/egress.py`. It checks destination, offline state, and private-value matches in URLs, headers and bodies, disables redirects, and records sent/blocked/failed attempts. Local model requests reject non-loopback destinations and bypass HTTP proxies. Keys are redacted from the visible ledger. The application serves no third-party scripts, fonts, analytics or images, and does not use browser localStorage for health data.

The ledger records app-gateway activity. The static import audit is NOT proof of process/OS network isolation, nor a complete semantic PHI detector. Network integrations were tested with local fake services. Production hardening, clinical review and real service/provider validation remain outstanding. External source links and OS geolocation have their own behavior; the app's ledger does not capture those requests.

## Tests

```sh
python3 -m unittest discover -v
python3 scripts/audit_egress.py
node --check static/app.js
```

Tests cover insured/self-pay branches, benefit arithmetic, coverage dates, unknowns, premium-inclusive comparisons, ranking changes, quote scope, encrypted persistence, booking confirmation, cross-origin/rebinding controls, request disclosure, and HTTP search/model integration with local fakes. The HTTP suite needs permission to bind loopback ports in a sandbox.

The older `triage.py`, `bills.py` and `costs.py` scaffold is not connected to this UI. It has not been validated as a clinical product. The new calculation module is `benefits.py`.
