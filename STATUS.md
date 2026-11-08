# FirstVisit — Current evidence and remaining work

Updated November 8, 2026 (America/New_York). Product goals: [PLAN.md](PLAN.md), [English](PLAN.en.md). This is an evidence snapshot for the source and verification reports in this repository; publication is separate from validation.

## Implemented

- Encrypted health profiles, visit feedback, relevant reminders, and per-fact source/review metadata for newly reviewed information. Older entries retain an explicit missing-date state.
- Three coverage branches, reviewed SBC intake, deterministic costs, explicit unknowns and separately labeled public NUSHP references.
- Default insured-student example: illustrative Northeastern student in Brookline 02445; two real clinic-location sources, with no invented price, network or appointment claims.
- External candidate intake: source URL, exact location, date and description. No background fetch; candidate remains unconfirmed until supported.
- Dated office answers: availability, language, referral requirement and referral obtained; service/plan/language scope, history and 30-day reconfirmation. Negative availability prevents supported-cost recommendation without deleting the candidate. Required referral creates a follow-through task.
- Existing quote/network/service confirmation updates the matching candidate. Cash quotes over 30 days old stop supporting cost claims.
- Home surfaces unfinished journeys and a concrete next question; saved journeys restore the results view.
- Candidate-specific call-script preparation: a built-in template, or the local model (Ollama, `qwen3.5:2b`) translating each fixed English line into the user's language with the English kept above it. Health history is not sent to the model. Works offline. In testing, free-form model drafts invented facts (for example "no referral needed"), so the model is limited to line-by-line translation and falls back to the labeled template if lines don't match.
- Gateway, DLP, ledger, offline controls and synthetic preflight self-check. Private reply text is protected; forgetting a plan also removes its derived SBC benefits.
- Disposable rehearsal launcher and prepared demo, submission, user-test and release documents under docs/.

## Verification

- Latest automated results: see [fresh install report](verification/install.json). It runs the complete suite, static network-import audit, JavaScript syntax check and independent receiver validation in a fresh temporary source copy and venv.
- [Receiver observation](verification/privacy-receiver.json): separate app process; one public synthetic search received, two HTTP/redirect failures accounted for, sensitive URL/header/body attempts blocked, no redirect follow or offline request received. Offline template and saved-case read passed. This is controlled loopback observation, not OS-wide capture or real API acceptance.
- Live Exa and Tavily acceptance: the app's preview → explicit approval → live-search path returned 12 candidates for a synthetic primary-care query near Brookline, MA 02445. The preview named both exact queries and destinations; the ledger recorded both requests as sent, redacted credentials, and contained none of the synthetic health-detail sentinels. A synthetic HTTP 401 was ledgered as an error, and offline mode blocked a search before network access. This validates the search integration, not the clinical accuracy of returned listings or clinician network status.
- Browser rehearsal: the disposable NEU example showed the 2026–27 annual fee separately from unknown personal costs and exact provider network. A separate disposable live-search session showed the exact Brookline query and recipients before approval, returned 12 leads, showed unknown prices and provider-confirmation prompts, blocked the synthetic privacy probe, enabled offline mode, and returned to the saved journey. Existing manual-candidate, office-reply, preparation and referral-required flows were also rehearsed. These are synthetic browser checks, not user research.
- [Local model acceptance](verification/ollama.json): the app called the real installed model over loopback with its offline switch on and got a Chinese translation of the fixed script. A non-loopback model URL was refused, an unreachable model fell back to the labeled template, the comparison was unchanged, there was no gateway traffic during drafting, and the private-history sentinel was not sent to the model. The report records whether a default network route existed at the time; the browser flow was also checked in Chrome. This does not review translation quality clinically.
- No real patient details were sent. Exa and Tavily received synthetic public search queries only; no clinic or insurer was contacted, no member login was used, and no interview or completed appointment is claimed.

## Integrations

| Item | State | Acceptance |
|---|---|---|
| Ollama | Passed with `qwen3.5:2b`: loopback-only, Chinese output, offline switch on, labeled fallback, no change to costs or safety rules | Translation quality is model-dependent and the user reviews it; labeled templates remain the fallback |
| Tavily / Exa search | Browser preview/approval and live search passed with synthetic Brookline inputs; privacy block and offline controls were also checked | Both APIs returned leads and gateway activity was recorded; this does not verify results, prices, appointments or network participation |

## External evidence still missing

1. **Current NUSHP cost sharing.** Official 2026–27 dates/annual fee are available, but linked Summary of Benefits and SBC PDFs are 2025–26. Do not auto-apply their copays to the current year.
2. **Exact provider participation and real costs.** An official BILH profile for Dr. Eric L. Hwang lists primary care at 1180 Beacon Street, says he is currently accepting new patients, and includes Blue Cross Blue Shield - MA among accepted plans. This is stronger public evidence for one lead, but it does not verify the exact NUSHP product/network, a bookable appointment, or any visit price. The insurer directory request returned HTTP 403; no private login was used. Exact-plan, service and cost confirmation is still needed.
3. **Actual target-user research.** Protocol prepared; no participants, quotes or willingness-to-pay evidence claimed.
4. **Video and submission.** Script and submission text prepared. Actual recording, upload, team details, competition-rule verification, repository publication and submission receipt remain outstanding.

These require outside evidence or external publication; prepared documents and tests do not close them.

## Public reference sources

- [NEU annual dates and fees](https://studenthealthplan.northeastern.edu/effective-dates-costs/): annual period 2026-09-01 through 2027-08-31; $3,049 student annual charge. Not member-specific coverage or monthly premium.
- [NEU highlights](https://studenthealthplan.northeastern.edu/highlighted-benefits/): undated copay highlights are leads requiring year confirmation, not calculation inputs.
- [Official BCBSMA lookup](https://member.bluecrossma.com/fad): use exact product from ID card/MyBlue and confirm clinician, address and service; NEU public guidance says PPO or EPO.
- [BILH Dr. Eric L. Hwang](https://primarycare.bilh.org/details/6789/eric-hwang-primary_care-brookline): official profile lists 1180 Beacon Street, currently accepting new patients and Blue Cross Blue Shield - MA. This is not exact NUSHP-product/network or price confirmation.
- [Brigham Brookline](https://www.massgeneralbrigham.org/en/locations/brookline-ma/brigham-and-womens-primary-care-associates-of-brookline-loc0000280904): 1 Brookline Place Suite 225, 02445.
- [BILH Beacon Street](https://bilh.org/locations/bilh-pc-1180-beacon): 1180 Beacon Street, 8th floor, 02446.

## Delivery materials

- [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md): clear real/manual/fictional distinctions and no-model fallback.
- [DEVPOST_DRAFT.md](docs/DEVPOST_DRAFT.md): reviewable copy, unsubmitted.
- [USER_VALIDATION.md](docs/USER_VALIDATION.md): consent, tasks, observations and acceptance protocol.
- [RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md): local verification and remaining external handoff.

Use Git for chronology, README for actual usage, PLAN for goals and acceptance. The parent HEALTHCARE_NAVIGATOR_SYSTEM_PLAN.md is a historical proposal.
