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
- Candidate-specific template preparation; works offline. The local text agent now has real Ollama acceptance; microphone and speech remain a later stage.
- Gateway, DLP, ledger, offline controls and synthetic preflight self-check. Private reply text is protected; forgetting a plan also removes its derived SBC benefits.
- Disposable rehearsal launcher and prepared demo, submission, user-test and release documents under docs/.

## Verification

- Local agent change: 99 automated tests passed, including real HTTP extraction/review/replay protection, plus static network-import audit and JavaScript syntax. This change has not had a fresh-install rerun or browser visual acceptance: Computer Use permissions were unavailable.
- Real `qwen2.5:3b` acceptance: see [local agent report](verification/agent-local.json). Nine synthetic Chinese/English inputs plus a confirmed two-fact workflow, explicit review, saved language/availability evidence and deterministic ranking; no actual clinic contacts or user health data. This small acceptance set is not a general model reliability guarantee.
- Earlier baseline automated results: see [fresh install report](verification/install.json). It runs the complete suite, static network-import audit, JavaScript syntax check and independent receiver validation in a fresh temporary source copy and venv.
- [Receiver observation](verification/privacy-receiver.json): separate app process; one public synthetic search received, two HTTP/redirect failures accounted for, sensitive URL/header/body attempts blocked, no redirect follow or offline request received. Offline template and saved-case read passed. This is controlled loopback observation, not OS-wide capture or real API acceptance.
- Browser rehearsal: profile creation, NEU example, manual candidate save, negative availability reply, current-provider preparation, home continuation, synthetic privacy self-check and offline saved preparation. Latest referral-required flow retains an obtain-referral task.
- No real patient details, credentials, provider calls, member login, interviews or completed appointments were used in these checks.

## Integration status

| Item | State | Acceptance |
|---|---|---|
| Ollama | Installed locally with `qwen2.5:3b`; bounded text-agent acceptance recorded separately | See `verification/agent-local.json`; microphone, speech playback and broader preparation-language acceptance remain outside this pass |
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

## Local text-agent scope

- Results → **本地助手 / Local assistant** opens deterministic task/cost tools and a
  single-turn local Ollama router for dated office-reply proposals.
- Only selected-clinic language, availability, referral-required and referral-obtained
  records can be proposed. Exact evidence quotes and explicit human review are required;
  source/date are supplied by the reviewer. Questions cannot become confirmation facts.
- Drafts remain in memory, expire after ten minutes, and are invalidated on task change,
  superseding turns, locking or forgetting. No conversation history is persisted.
- Language replies now affect fit ordering and reasons. Current negative availability
  retains a clinic as a backup. Costs, insurance participation and booking state are
  not agent-writable.
- Zocdoc insurance IDs require explicit exact-product selection in the plan form;
  substring matching on a typed name was removed. The external filter is not proof
  of participation.
- Reproduce with `python3 scripts/verify_agent.py`; public search credentials are disabled
  and the vault is disposable. Microphone, transcription and audio playback are not built.

## Navigation and personalization update

Visible Back/home controls, completed-step editing and in-memory browser navigation
now preserve unsaved form entries within this tab. History stores opaque IDs only;
locking/forgetting invalidates private snapshots. Results show care preferences,
sorting rationale and next contact actions before optional general guidance. Care
language, budget and priority can be changed in place; home next actions refresh
from the saved task. Nine Node checks cover back/forward drafts, rerenders, isolation, clearing, expired
IDs, actual preference rendering and candidate-specific next actions. Browser visual verification remains
unavailable without Computer Use permission; unsaved drafts do not survive reload.
