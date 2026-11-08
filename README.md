# FirstVisit

**Optional browser dictation:** spoken content may be sent to a browser-selected provider. FirstVisit cannot guarantee provider retention, training exclusion or deletion. On-device mode requires browser support and never silently falls back. See [voice privacy boundary](docs/VOICE_PRIVACY.md).

Product goals and acceptance criteria: [PLAN.md](PLAN.md) ([English](PLAN.en.md)). Current validation and remaining work: [STATUS.md](STATUS.md).

**A private health companion for people new to US healthcare.** FirstVisit starts with you and your health. It keeps an encrypted health profile on your own computer, tells you what to do next, helps you choose where to go and what it will cost, and gets more useful after every visit.

Built for Hack1984 (Privacy-First track), first for international students in Boston. This is a working prototype, not a clinical product: it never diagnoses, and every suggestion comes from fixed rules with an official source.

## Start

```sh
git clone https://github.com/gaofang86/Hack-FK.git
cd Hack-FK
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Use Python 3.11 or newer. On macOS, if `python3.11` is not installed, install it with `brew install python@3.11`. Activate `.venv` again with `source .venv/bin/activate` whenever you open a new terminal.

Open http://127.0.0.1:8766. The first time, you build your health profile and choose a passphrase that encrypts it. There's no account and no server-side copy. The passphrase can't be recovered; "Start a new profile" on the unlock page erases the old one. Don't commit the vault or `.env`.

To try it with fictional data instead:

```sh
python3 run.py --preview
```

Open http://127.0.0.1:8767. This uses a disposable vault that never locks itself, turns off public search, and shows a "Temporary preview" label. Use only made-up details. If you lock it, the test passphrase is `firstvisit-preview-only` (shown on the unlock page). Inside a visit, "Explore a fictional example" loads fictional Boston clinics and a fictional plan.

## Student insurance scenario: NEU / 02445

On home, choose **Explore NEU / 02445**, or use **Student insurance scenario** in the visit sidebar. This is the default example for an insured student, not an assertion about your own enrollment. It uses an illustrative adult in Brookline ZIP 02445 (no street address), a NUSHP plan name awaiting exact product/year confirmation, and real primary-care location sources. It does not replace your saved profile or prefill unverified benefits.

The Brookline directory includes Brigham primary care at 1 Brookline Place, 02445, and BILH primary care at 1180 Beacon Street, 02446. Prices, clinician-level network, new-patient acceptance and appointment availability remain unconfirmed. No ZIP-based travel distance is invented. The scenario now shows a sourced 2026–27 reference: annual period September 1, 2026–August 31, 2027 and $3,049 student annual fee. These reference values do not populate personal premiums, active coverage or remaining balances. NEU’s linked benefit PDFs still open 2025–26 files, so current-year cost sharing remains unverified. Official directory guidance, exact-provider verification steps and NUSHP contact details are included.

Results separate supported visit-cost comparisons from options needing confirmation. Each candidate has its own questions and preparation script. Save scoped quote/network answers with **Add quote / confirmation** to recalculate; record appointment outcomes separately.

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

Visit date, what matters most (fit, price, rating, distance), budget, then location. If you approve live search, the query includes care type and city/state/ZIP; the current app flow does not include your insurer or health details. You see the exact query and recipients before anything is sent, and you can choose the local directory only.

### 4. What to expect (while the search runs)

Computed with fixed rules on your device, with no model and no network. It shows where you could go, in order, and what you might pay: [FAIR Health's](https://www.fairhealthconsumer.org/en/insurance-basics/healthcare/emergency-care-and-urgent-care) example fees (urgent care $300, ER $1,000) run through your own plan. It's labeled as an illustration, not a quote. A copay plan never gets a guessed ER cost. It also covers what to bring and what to ask.

### 5. Results: different help for each coverage situation

| Situation | What you see first |
| --- | --- |
| **A. Has insurance** | What we know about your plan, questions to confirm before you go (copyable), and tips: use in-network care; preventive care may be free |
| **B. No insurance** | Check you're not already enrolled by your school; cheapest options first; [community health centers](https://findahealthcenter.hrsa.gov/), [free clinics](https://nafcclinics.org/find-clinic/), [hospital financial assistance](https://www.irs.gov/charities-non-profits/financial-assistance-policies-faps), [Good Faith Estimates](https://www.cms.gov/newsroom/fact-sheets/no-surprises-understand-your-rights-against-surprise-medical-bills); scripts for asking about price and help |
| **C. Choosing a plan** | Everything in B, plus **Compare plans**: pick the care you expect this year (pre-filled from your profile), enter up to three plans, and get a yearly total = premiums + care, capped at the out-of-pocket maximum. A plan with unknown or uncovered care is never ranked. |

**External provider lookup (Zocdoc).** `app/sources.py` turns your situation into a prefilled Zocdoc results link: kind of care (urgent care, primary care illness, annual physical, follow-up), your ZIP, and, only if you explicitly select a supported exact product in the plan form, that insurance filter. A typed plan name never selects a product. The currently supported filter is Blue Cross Blue Shield of Massachusetts · Blue Care Elect (PPO). This does not establish that it is your current NUSHP product or that any clinician participates. It opens in your own browser, so FirstVisit sends nothing; the card lists exactly what Zocdoc will see. The IDs were read from zocdoc.com result URLs on 2026-11-07. They're not a documented API and may change. Sources share one `describe()` shape, so a Zocdoc API source can replace the link once partner credentials arrive (requested 2026-11-07, not yet granted).

Below that is the shortlist: personal cost, language, rating and distance, each labeled with its source. Unknown stays unknown, never $0. You can add a confirmed quote, prepare a call script (built-in template, or with your local model each English line followed by its translation), and track the appointment.

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
| Local model | Ollama on loopback only (verified with `qwen3.5:2b`). Preparation translates the fixed call script line by line without health history. The optional care-task agent reads submitted office replies and proposes reviewed records; costs and safety rules remain deterministic. Labeled template when unavailable; no cloud fallback |
| Booking | You book on the provider's site, then record it; no automatic booking |

## Connect services

Copy `.env.example` to `.env` and add `TAVILY_API_KEY` or `EXA_API_KEY`, then restart. For call scripts in your language, install [Ollama](https://ollama.com), then run:

```sh
ollama pull qwen3.5:2b
```

In a visit, choose **Prepare this visit → Use my local model**. If the model isn't running, the app says why and shows the English template instead.

## Privacy

- Every outbound app-backend request goes through `app/egress.py`. Optional browser-service dictation is a separate browser-controlled path outside this gateway and ledger. It checks the destination and the offline switch, URL-decodes and scans URLs, headers and bodies for your private values, refuses redirects, and records sent, blocked and failed attempts in a ledger.
- Protected values include your profile (conditions, medications, allergies, follow-ups), visit reasons and notes, and the symptoms you picked.
- The local model only accepts loopback addresses and bypasses HTTP proxies.
- The app loads no third-party scripts, fonts, analytics or images, and keeps no health data in browser storage.

**Scope.** The ledger covers the app's own gateway, not the whole operating system. The static import audit checks that only `egress.py` opens connections; it isn't a full security audit or a semantic PHI detector. Automated tests use local fakes; live Tavily/Exa and local-model checks are recorded separately in STATUS.md and `verification/ollama.json`.

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

## Continue a care task

- On results, **Add a provider you found** saves a candidate and exact address from a public source without fetching the URL. Service, price and network remain unconfirmed.
- **Record office reply** records dated, sourced answers about new-patient appointments, language and referrals. Unknown answers remain open; replies over 30 days old require reconfirmation. A required referral remains a task until recorded as obtained. A negative availability reply retains the candidate as a backup, outside supported-cost comparisons.
- **Add quote / confirmation** retains the separate service, scoped cash quote and exact-plan network controls. Cash quotes older than 30 days become unknown until reconfirmed.
- Home shows unfinished care journeys and a concrete next question. **What we know** shows source/review dates for facts recorded since this update; older entries explicitly lack dates.
- Privacy includes a **synthetic self-check** that exercises gateway preflight without a network call. It is not a medical-data detector or OS isolation guarantee.

## Rehearsal and delivery

```sh
python3 scripts/rehearse.py
```

Open http://127.0.0.1:8767. This creates a disposable fictional profile and a real-source NEU / 02445 journey, with no search credentials. Do not run it alongside another preview using port 8767.

Prepared materials: [demo script](docs/DEMO_SCRIPT.md), [submission draft](docs/DEVPOST_DRAFT.md), [user-test protocol](docs/USER_VALIDATION.md), [release checklist](docs/RELEASE_CHECKLIST.md). Interviews, recording, publication and submission are not claimed as completed.

Live Tavily/Exa acceptance passed for a synthetic Brookline query; see STATUS.md for scope and limits. Live discovery requires your own API key. The local model (Ollama, `qwen3.5:2b`) passed its acceptance check; see `verification/ollama.json`. Both stay optional: template preparation, the local directory and manual candidates work without them.

## Tests

```sh
python3 -m unittest discover -v
python3 scripts/audit_egress.py
node --check static/app.js
node --check static/navigation.js
node --check static/dictation.js
node --test tests/test_navigation_ui.cjs tests/test_personalized_ui.cjs tests/test_care_today_ui.cjs tests/test_dictation.cjs tests/test_home_journey_ui.cjs
```

The Python suite includes the local care agent as well as the following workflows. Tests cover safety rules and the emergency block, the care-today path, cost math, the what-to-expect illustration, SBC reading (including PDFs whose text splits words across lines), Zocdoc link building (IDs, unknown plans, no health details in the URL), the profile (rules, refills, follow-ups, persistence, forgetting), visit recording, A/B/C guidance and plan comparison, the encrypted vault, the DLP filter, the local-model fallback and line-by-line translation, and HTTP hardening (cross-origin and DNS-rebinding checks, path traversal). The HTTP tests need permission to bind loopback ports.


Reproducible acceptance checks (use only synthetic data):

```sh
python3 scripts/verify_privacy.py --out verification/privacy-receiver.json
python3 scripts/verify_install.py
python3 scripts/verify_ollama.py --out verification/ollama.json   # needs Ollama running; run with Wi-Fi off to record no network route
```

The first observes a separate test app process using a controlled loopback receiver. The second downloads requirements into a fresh temporary virtual environment and runs tests, the import audit, JS syntax and receiver checks. Reports are under `verification/`; neither validates real API keys, exact physician participation or production network isolation.

## Local care-task assistant (text first)

On a saved journey's results page, choose **本地助手 / Local assistant**.
**View task** and **View costs** read deterministic saved evidence and work without
Ollama, including with the app's offline switch on. To interpret Chinese or English
text locally, start Ollama and install the configured model:

```sh
ollama serve
# In a second terminal:
ollama pull qwen2.5:3b
```

The translator uses `OLLAMA_MODEL` (default `qwen3.5:2b`); the agent uses
`OLLAMA_AGENT_MODEL` (default `qwen2.5:3b`). The latter requires JSON-schema support.
During merge acceptance the installed `qwen3.5:2b` runtime returned
`structured output is unavailable`, so these paths are configured independently;
there is no silent model substitution or cloud fallback.

Select the exact clinic and enter an office reply, such as
“这家诊所有中文翻译，但目前不收新病人。” The local model proposes separate language
and availability facts. Review each quoted span and result, omit unwanted facts,
and supply the actual contact/source and date before **Confirm and save**.
No facts are written during extraction. Model output must pass an allowlist and
verbatim-evidence checks; a question cannot be saved as an office confirmation.
The model can still misunderstand meaning, so review is required. Invalid output
never silently becomes a confirmed fact; the manual office-reply form stays available.

Confirmed language answers update fit ordering and reasons; a negative availability
answer retains the clinic as a backup. Unknown or expired answers do not confirm
support. Prices, plan participation and bookings cannot be written by this agent.
Drafts expire after ten minutes, are superseded by the next turn for that journey,
and are invalidated by task changes. Locking or forgetting clears in-memory drafts.
Conversation text is not saved; only reviewed evidence spans become encrypted office
records. There is no cloud fallback. This is a bounded, single-turn tool router,
not an autonomous medical advisor. The unified homepage now adds optional browser dictation as a separate input feature; speech playback and autonomous voice conversation are not implemented.

```sh
python3 scripts/verify_agent.py
```

This opt-in check uses the real configured local model, synthetic Chinese text, a
disposable vault and the app's offline switch. Results go to
`verification/agent-local.json`. It does not verify microphone input, browser layout,
OS-wide isolation, actual clinic contacts or real insurance participation.

## Navigation and preferences

- A visible Back control and My health home link appear on task and secondary pages,
  including narrow screens. Completed intake steps can be reopened directly.
- Browser Back/Forward restores in-tab drafts. Private entries remain in memory;
  browser history contains only opaque navigation IDs, never health values or
  passwords. Locking or forgetting clears the navigation snapshots. A page reload
  does not recover unsaved drafts; saved journeys remain in the vault.
- Results lead with the current care need, care language, budget, payment path and
  sorting basis, then a concrete next action. **Edit preferences** updates the saved
  task and immediately reorders its existing candidates without a public search.
- Generic insurance guidance and example scenarios are available behind details,
  rather than preceding the user's own task. Home continuation refreshes saved next
  actions after office replies or preferences change.
- Navigation state has Node regression coverage; a browser visual pass still needs
  Computer Use permission and is not claimed by these unit checks.

## Unified homepage, task scenarios and optional lab reports

Start with a goal rather than a complete health profile. First visit, current concern,
report preparation and follow-through create the same care-task record. No report is
required, including when the report starting point is chosen. A passphrase is needed
only to save the first task. Relevant age/coverage questions remain in the care-search
flow; this homepage does not replace the fixed safety checks.

A task can be prepared without searching. When finding care, the existing intake,
disclosure preview, provider shortlist, preferences, confirmations and visit feedback
extend that same task ID. Personal goals and linked reports remain available from
results. A reported warning in the goal cannot bypass the emergency/same-day guard.

**Add lab PDF** supports a bounded text-export format and the FirstVisit demo copy,
not arbitrary reports, scans or OCR. It previews source facts and verbatim evidence;
reviewers may correct or omit each item before confirmation. The original PDF is not
retained. Reviewed rows and source fingerprints are encrypted in the vault. Report
flags never create diagnoses, follow-up orders or appointments. Personal clinician
notes include linked facts; booking scripts and public searches do not. Forgetting a
report clears its links and derived preparation. Current parser scope is deliberately
explicit: an unsupported report does not prevent continuing the task without it.

```sh
python3 scripts/start_local_demo.py
```

Open http://127.0.0.1:8768. This uses a persistent encrypted vault outside the repo,
asks for your own passphrase and loads no public-search credentials. It does not
replace the separate disposable fictional preview on 8767. Select a report yourself;
no real report is bundled or committed by this feature.

Local report acceptance (output contains counts only, not lab values):

```sh
python3 scripts/verify_report_journey.py --pdf /absolute/path/to/local-report.pdf
```

See `verification/report-journey.json` for the controlled local report workflow, and
`docs/VOICE_PRIVACY.md` for browser processing, content retention uncertainty and the
limits of our ledger. Browser-service dictation needs explicit disclosure consent
and is unavailable while the app's offline switch is on. It only appends editable text
and never submits a task automatically. Real microphone and browser visual acceptance
are separate from mocked API unit tests.

## Interface language

The header offers EN / 中文. English is the default, with a larger headline; Chinese
uses a more compact type scale. Homepage copy is shown in one selected language,
not as a bilingual subtitle pair. Interface preference is independent of care language
and dictation language and is the only value stored under `firstvisit.ui-language`
in browser localStorage. Switching updates text in place, preserving drafts and form
values. If storage is unavailable, the selection still works for this page session.
Clinical source text, report data, user-entered text, provider names and private
preparation are preserved rather than automatically translated. Static interface
copy uses a local catalog; no translation service receives page content.

Homepage starting points now use everyday labels: find a regular doctor, a new
health concern, discuss test results, and a next step recommended by a clinician.
Each has a short description and a contextual writing prompt. Choosing one changes
the prompt, not the user's words. The choice is optional: free-text-only requests
use a general task and can still add reports or enter the health-needs flow later.
Resuming an existing saved task is a separate control, not a follow-up category.
