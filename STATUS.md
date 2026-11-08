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
- Candidate-specific template preparation; works offline. Ollama remains deferred.
- Gateway, DLP, ledger, offline controls and synthetic preflight self-check. Private reply text is protected; forgetting a plan also removes its derived SBC benefits.
- Disposable rehearsal launcher and prepared demo, submission, user-test and release documents under docs/.

## Verification

- Latest automated results: see [fresh install report](verification/install.json). It runs the complete suite, static network-import audit, JavaScript syntax check and independent receiver validation in a fresh temporary source copy and venv.
- [Receiver observation](verification/privacy-receiver.json): separate app process; one public synthetic search received, two HTTP/redirect failures accounted for, sensitive URL/header/body attempts blocked, no redirect follow or offline request received. Offline template and saved-case read passed. This is controlled loopback observation, not OS-wide capture or real API acceptance.
- Browser rehearsal: profile creation, NEU example, manual candidate save, negative availability reply, current-provider preparation, home continuation, synthetic privacy self-check and offline saved preparation. Latest referral-required flow retains an obtain-referral task.
- No real patient details, credentials, provider calls, member login, interviews or completed appointments were used in these checks.

## Deferred integrations (user decision)

| Item | State | Acceptance |
|---|---|---|
| Ollama | Pending; no installation or real-model pass claimed | PLAN.md section 9; labeled templates are available |
| Tavily / Exa API key | Pending; no credentials supplied or real-service pass claimed | Configure one service locally and verify approved public queries, results, failures and ledger |

## External evidence still missing

1. **Current NUSHP cost sharing.** Official 2026–27 dates/annual fee are available, but linked Summary of Benefits and SBC PDFs are 2025–26. Do not auto-apply their copays to the current year.
2. **Exact provider participation and real costs.** The two Brookline clinic sources establish location/services, not clinician-level network, complete quote, new-patient acceptance or appointment availability. The official directory request returned HTTP 403; no private login was used. User/provider/insurer confirmation is needed.
3. **Actual target-user research.** Protocol prepared; no participants, quotes or willingness-to-pay evidence claimed.
4. **Video and submission.** Script and submission text prepared. Actual recording, upload, team details, competition-rule verification, repository publication and submission receipt remain outstanding.

These require outside evidence or external publication; prepared documents and tests do not close them.

## Public reference sources

- [NEU annual dates and fees](https://studenthealthplan.northeastern.edu/effective-dates-costs/): annual period 2026-09-01 through 2027-08-31; $3,049 student annual charge. Not member-specific coverage or monthly premium.
- [NEU highlights](https://studenthealthplan.northeastern.edu/highlighted-benefits/): undated copay highlights are leads requiring year confirmation, not calculation inputs.
- [Official BCBSMA lookup](https://member.bluecrossma.com/fad): use exact product from ID card/MyBlue and confirm clinician, address and service; NEU public guidance says PPO or EPO.
- [Brigham Brookline](https://www.massgeneralbrigham.org/en/locations/brookline-ma/brigham-and-womens-primary-care-associates-of-brookline-loc0000280904): 1 Brookline Place Suite 225, 02445.
- [BILH Beacon Street](https://bilh.org/locations/bilh-pc-1180-beacon): 1180 Beacon Street, 8th floor, 02446.

## Delivery materials

- [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md): clear real/manual/fictional distinctions and no-model fallback.
- [DEVPOST_DRAFT.md](docs/DEVPOST_DRAFT.md): reviewable copy, unsubmitted.
- [USER_VALIDATION.md](docs/USER_VALIDATION.md): consent, tasks, observations and acceptance protocol.
- [RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md): local verification and remaining external handoff.

Use Git for chronology, README for actual usage, PLAN for goals and acceptance. The parent HEALTHCARE_NAVIGATOR_SYSTEM_PLAN.md is a historical proposal.
