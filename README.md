# FirstVisit

**A private health companion for people new to US healthcare.** FirstVisit starts with you and your health. It keeps an encrypted health profile on your own computer, tells you what to do next, helps you choose where to go and what it will cost, and gets more useful after every visit.

Built for Hack1984 (Privacy-First track), first for international students in Boston. This is a working prototype, not a clinical product: it never diagnoses, and every suggestion comes from fixed rules with an official source.

## Start

```sh
git clone https://github.com/gaofang86/Hack-FK.git
cd Hack-FK
python3 -m pip install -r requirements.txt
python3 run.py
```

Open http://127.0.0.1:8766. The first time, you build your health profile and choose a passphrase that encrypts it. There's no account and no server-side copy. The passphrase can't be recovered; "Start a new profile" on the unlock page erases the old one. Don't commit the vault or `.env`.

To try it with fictional data instead:

```sh
python3 run.py --preview
```

Open http://127.0.0.1:8767. This uses a disposable vault that never locks itself, turns off public search, and shows a "Temporary preview" label. Use only made-up details. If you lock it, the test passphrase is `firstvisit-preview-only` (shown on the unlock page). Inside a visit, "Explore a fictional example" loads fictional Boston clinics and a fictional plan.

## How it works

### 1. Your health profile (the part that accumulates)

Stored only in the encrypted vault:

- Birth year, optional sex (only used for sex-specific screenings), preferred language
- Ongoing conditions, allergies
- Medications, with when each runs out
- Follow-ups a clinician asked for, with due dates
- Coverage: insured, not insured, or choosing a plan
- **Your plan's costs, read from its SBC.** Every US plan publishes a Summary of Benefits and Coverage on the same federal template. Upload the PDF (or paste its text) and `app/sbc.py` reads the deductible, out-of-pocket limit and the in-network cost for primary care, specialists, preventive care, urgent care, the ER, generic drugs and mental health. It uses fixed rules on your computer, with no model and no network. Each value shows the line it came from; you review and fix it before saving. Only the values and a SHA-256 fingerprint of the file are kept, not the file. From then on, the cost estimate, "what to expect" and the insured results page use your plan's real numbers for each kind of visit.

The home page ("Welcome back") shows:

- **Your to-dos.** Personal ones first (refills due within 14 days, follow-ups due within 30 days, overdue ones in red), then checkups and vaccines for your age and sex from the [USPSTF A and B recommendations](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations) and the [CDC adult immunization schedule](https://www.cdc.gov/vaccines/hcp/imz-schedules/adult-age.html). Each item links its source and can be ticked off.
- **Better choices.** For example: preventive care is often free in-network ([HealthCare.gov](https://www.healthcare.gov/coverage/preventive-care-benefits/)); community health centers charge by income ([HRSA](https://findahealthcenter.hrsa.gov/)).
- **Your visits.** A timeline of past visits.
- **What we know.** Every saved item, each with Forget, plus "Forget everything".

### 2. What do you need today?

- **I feel unwell** or **I'm not sure:** one page, "What's bothering you?", grouped by body part (chest and breathing, head, belly, arms and legs, and so on). Serious and everyday problems sit together. Fixed local rules (`app/triage.py`) check each pick and any typed text right away:
  - **Emergency** (for example chest pain, throwing up blood, thoughts of self-harm): call buttons for 911, 988 or Poison Control. Price comparison is blocked, in the browser and on the server.
  - **Care today** (for example an eye injury): "Find care today" looks for urgent care and campus clinics.
  - Otherwise you continue to planned care.
- **I'm okay:** pick a checkup, refill or follow-up. No symptom questions.

Age, language, coverage, conditions and medications are filled in from your profile.

### 3. When and where

Visit date, what matters most (fit, price, rating, distance), budget, then location. **Location is the only detail a public search ever uses.** You see the exact query and recipients before anything is sent, and you can choose the local directory only.

### 4. What to expect (while the search runs)

Computed with fixed rules on your device, with no model and no network. It shows where you could go, in order, and what you might pay: [FAIR Health's](https://www.fairhealthconsumer.org/en/insurance-basics/healthcare/emergency-care-and-urgent-care) example fees (urgent care $300, ER $1,000) run through your own plan. It's labeled as an illustration, not a quote. A copay plan never gets a guessed ER cost. It also covers what to bring and what to ask.

### 5. Results: different help for each coverage situation

| Situation | What you see first |
| --- | --- |
| **A. Has insurance** | What we know about your plan, questions to confirm before you go (copyable), and tips: use in-network care; preventive care may be free |
| **B. No insurance** | Check you're not already enrolled by your school; cheapest options first; [community health centers](https://findahealthcenter.hrsa.gov/), [free clinics](https://nafcclinics.org/find-clinic/), [hospital financial assistance](https://www.irs.gov/charities-non-profits/financial-assistance-policies-faps), [Good Faith Estimates](https://www.cms.gov/newsroom/fact-sheets/no-surprises-understand-your-rights-against-surprise-medical-bills); scripts for asking about price and help |
| **C. Choosing a plan** | Everything in B, plus **Compare plans**: pick the care you expect this year (pre-filled from your profile), enter up to three plans, and get a yearly total = premiums + care, capped at the out-of-pocket maximum. A plan with unknown or uncovered care is never ranked. |

**Real in-network providers (Zocdoc).** `app/sources.py` turns your situation into a prefilled Zocdoc results link: kind of care (urgent care, primary care illness, annual physical, follow-up), your ZIP, and, if your saved plan matches one we have IDs for, your exact plan. Today that's Blue Cross Blue Shield of Massachusetts · Blue Care Elect (PPO), Northeastern's student plan. It opens in your own browser, so FirstVisit sends nothing; the card lists exactly what Zocdoc will see. The IDs were read from zocdoc.com result URLs on 2026-11-07. They're not a documented API and may change. Sources share one `describe()` shape, so a Zocdoc API source can replace the link once partner credentials arrive (requested 2026-11-07, not yet granted).

Below that is the shortlist: personal cost, language, rating and distance, each labeled with its source. Unknown stays unknown, never $0. You can add a confirmed quote, prepare a call script (template, or a local Ollama draft), and track the appointment.

### 6. After the visit

"I went · record the visit" (or "+ Record a visit" on home) asks when, where, why and what the clinician said. Then it asks about new medicines, new follow-ups, new conditions, and which existing follow-up this visit completed. They merge into your profile without duplicates and become your next to-dos.

## What is real, manual, and fictional

| Capability | Current implementation |
| --- | --- |
| Profile, to-dos, visits, intake, safety check, scenarios, plan comparison | Working local UI and API |
| Storage | AES-256-GCM vault, scrypt key, file mode 0600; auto-lock after 15 idle minutes (not in preview) |
| Safety rules | Fixed rules in `app/triage.py`; not clinically validated |
| To-do rules | Fixed age and sex rules in `app/health.py`, each with a source checked 2026-11-07 |
| Boston primary-care directory | Two real clinics with official links; no invented prices, ratings or networks |
| Same-day directory | None in real mode; real urgent care results come only from live search. Demo mode has three fictional same-day clinics |
| Live search | Tavily and/or Exa; needs your own API key; results are leads to confirm |
| Personal prices | Deterministic copay or deductible/coinsurance math on your entered benefits and confirmed quotes |
| Reviews and distance | Unknown unless sourced; demo values are fictional |
| Local model | Ollama on loopback only, for visit-prep drafts; clearly labeled template when unavailable; no cloud fallback |
| Booking | You book on the provider's site, then record it; no automatic booking |

## Connect services

Copy `.env.example` to `.env` and add `TAVILY_API_KEY` or `EXA_API_KEY`, then restart. For local drafts, install Ollama and run:

```sh
ollama pull qwen2.5:3b
```

## Privacy

- Every outbound app request goes through `app/egress.py`. It checks the destination and the offline switch, URL-decodes and scans URLs, headers and bodies for your private values, refuses redirects, and records sent, blocked and failed attempts in a ledger.
- Protected values include your profile (conditions, medications, allergies, follow-ups), visit reasons and notes, and the symptoms you picked.
- The local model only accepts loopback addresses and bypasses HTTP proxies.
- The app loads no third-party scripts, fonts, analytics or images, and keeps no health data in browser storage.

**Scope.** The ledger covers the app's own gateway, not the whole operating system. The static import audit checks that only `egress.py` opens connections; it isn't a full security audit or a semantic PHI detector. Network integrations were tested against local fakes.

## Code map

| File | What it does |
| --- | --- |
| `app/health.py` | Profile, to-do and better-choice rules, visit recording |
| `app/triage.py` | Safety rules and warning-word scan |
| `app/navigation.py` | Intake validation and ranking |
| `app/benefits.py` | Visit cost arithmetic |
| `app/expect.py` | The "what to expect" page |
| `app/scenarios.py` | A/B/C guidance and plan comparison |
| `app/sources.py` | Provider sources (prefilled Zocdoc link; API later) |
| `app/sbc.py` | Reads a plan's SBC (PDF via `pypdf`, or text) into per-service costs |
| `app/egress.py` | The only network gateway, with DLP and ledger |
| `app/store.py` | Encrypted vault |
| `app/server.py` | Local HTTP API |
| `static/` | The whole UI (no build step) |

`app/bills.py` and `app/costs.py` are early drafts. They aren't connected yet.

## Tests

```sh
python3 -m unittest discover -v
python3 scripts/audit_egress.py
node --check static/app.js
```

There are 74 tests. They cover safety rules and the emergency block, the care-today path, cost math, the what-to-expect illustration, SBC reading (including PDFs whose text splits words across lines), Zocdoc link building (IDs, unknown plans, no health details in the URL), the profile (rules, refills, follow-ups, persistence, forgetting), visit recording, A/B/C guidance and plan comparison, the encrypted vault, the DLP filter, and HTTP hardening (cross-origin and DNS-rebinding checks, path traversal). The HTTP tests need permission to bind loopback ports.
