# FirstVisit — Pivot Plan (draft, pending confirmation)

> English version of [PLAN.md](PLAN.md). Sections 2 and 4 were updated at 17:30 EST to match the current code; the other sections are the 15:54 draft.

> Deadline: Sunday, 2026-11-08, 11:00 AM EST. It is now about 4 PM Saturday, leaving about 19 hours, which must also cover sleep, recording the video, and submitting.

## 1. One-line positioning

**FirstVisit: helps international students know where to go, how much it will cost, and what to say for their first doctor visit in the US. Health and insurance information stays on their own computer.**

- **Target user**: international students getting care in the US for the first time, starting with Northeastern University and its student health insurance plan.
- **Pain points**: they can't tell the ER, urgent care, the campus health center, and telehealth apart; they don't know what copay or in-network means; making an appointment by phone in a second language is stressful; they receive a bill or an EOB they can't understand and don't know whether to pay it.
- **How we differ from competitors**: Docus, Guava and ChatGPT Health interpret labs and medical records; Zocdoc books doctors. We guide the process before and after a visit, and our privacy can be proven: the search service only learns that "someone near 02115 is looking for urgent care", not why.
- **Out of scope**: diagnosis, lab interpretation, medical-record integrations, automatic booking, and healthcare systems outside the US.

## 2. Three scenarios (the product's main path)

### Step 0: Person first — start from the person's health

The product starts from caring about the person's health, not from a place or an identity. First understand the person's health, stored only on the device:

- **Age**: determines which preventive screenings and vaccines fit this person
- **Current health**: recent symptoms, chronic conditions, medications, allergies, ongoing treatment or follow-ups
- **Need**: what they need right now (see the three cases below)
- **Language**: native language, whether they need an interpreter
- **Insurance status**: has a plan / no plan / choosing a plan
- **Location**: just one dimension, used at the end to filter nearby options; also the only field sent to search services

No identity questions (student status, school, etc.).

### Health-based to-dos and better choices

Beyond answering this one need, the app proactively offers, based on the person's health:

- **Potential to-dos**: for example age-appropriate preventive screenings and vaccines, medications running out that need a refill, follow-ups that are due, regular checks for chronic conditions
- **Better choices**: for example telehealth or campus health instead of the ER when it isn't urgent; many plans cover preventive services at no cost; a cheaper generic medication; a check that can be done during this same visit

Rules:
- Every item comes from a deterministic rule with an official source and date (for example USPSTF screening recommendations, the CDC adult immunization schedule). The local model only explains them in the user's native language; it cannot generate recommendations itself.
- Only say "you could consider" and "you could ask your doctor". No diagnosis, and no decisions on the doctor's behalf.
- These to-dos are saved in the local vault and are still there the next time the app opens.

Insurance status only decides how the user pays. What comes first is what they need right now, so the first question is about the need:

1. **I feel unwell now**: run a local safety check first. Emergencies go straight to 911, the ER, 988 or Poison Control, **with no insurance questions at all**. Non-urgent cases continue.
2. **I have a specific service to arrange**: for example an appointment, a follow-up, a prescription refill, counseling, or a vaccine.
3. **I don't need care right now**: I just want to understand my insurance, or I'm choosing a plan.

Only then do we ask about insurance and split into three scenarios. **The three scenarios have different core questions, focus and first steps**, and finding a clinic is not necessarily the first step. They share only the Unperson foundation: the encrypted vault, the egress gateway and ledger, the local model, and the privacy proof.

### The three scenarios

| | **A. Has insurance** | **B. No insurance** | **C. Choosing a plan** |
|---|---|---|---|
| **Core question** | What does my plan cover, and how do I use it for the lowest cost? | Where is the cheapest care, and what resources might I not know about? | Which plan best covers what I need most? |
| **Focus** | **Benefits** | **Lowest price + possible coverage and resources to ask for help** | **Coverage vs. most-needed services** |
| **User input** | Plan name; copay, remaining deductible and coinsurance for this service; member details stay on the device | Need, location, budget | Most-needed services (regular medications, counseling, specialists, chronic-condition follow-ups, etc.), doctors they want to keep seeing, budget, candidate plans |
| **First step** | A **benefit summary** for this need: is it covered, is a referral or prior authorization needed, are preventive services free, what resources come with the plan (nurse line, telehealth) | **Check whether they are actually insured**: the school may have enrolled them in the student plan automatically. Then look at the cheapest options | **List the services they need most**, without searching for clinics |
| **What the app does** | Rank in-network options by what the user will actually pay; list questions to confirm with the insurer | Rank by self-pay price (missing quotes stay unknown); list resources: community health centers (income-based fees), free clinics, hospital financial assistance, state programs (eligibility must be confirmed by the user); explain the right to a written estimate when uninsured or self-paying (Good Faith Estimate, under the No Surprises Act); provide scripts for asking for an estimate or a discount | For each candidate plan, mark every most-needed service: covered or not, what it costs, whether the preferred doctors are in network; estimate the yearly total (premiums + expected use); flag what each plan doesn't cover or needs attention; link official sources (school plan, Health Connector) |
| **Last step** | Visit preparation: phone script, condition card, what to bring | Visit preparation, plus scripts for estimates and financial help | Enroll through the official channel; **no enrollment inside the app** |
| **Can move to** | — | Wants to buy a plan → C | After choosing → A |

> Note: every resource and rule needs an official source and date. Eligibility is never inferred; the app only tells users where to confirm it.

### Current code and gaps (17:45)

| Part | Current code | Gap |
|---|---|---|
| Entry order | **Location** first → insurance → need (this is the current code's order: location first) | Change to person first: health and need (with safety check) → age, language, insurance → scenario + health to-dos; ask for location only when it is time to find a place. `triage.py` is drafted but not connected |
| A. Has insurance | `benefits.insured_cost` calculates personal cost and compares it with self-pay | No benefit summary, no referral or preventive-service guidance; the results page is still centered on a clinic list |
| B. No insurance | `benefits.cash_cost` ranks by self-pay price; there is a "check your school account" hint | No resource list, no Good Faith Estimate guidance or scripts |
| C. Choosing a plan | `benefits.comparison` only covers one visit + N premium payments | No "most-needed services" input, no multi-plan comparison, no yearly estimate |
| Results page | All three scenarios share one clinic-list template | Each scenario needs its own results page |

## 2b. Original MVP demo flow (draft, partly unbuilt)

1. **Encrypted vault**: set a passphrase. No account, no server.
2. **My information**: name, date of birth, native language, allergies, medications and medical history (never sent); city, state and ZIP (sent when finding clinics); insurer name (the user chooses whether it is sent); member ID and group number (never sent); copays, deductible and coinsurance copied from the insurance card or SBC.
3. **What's wrong → where to go**
   - Check symptoms, add a free-text description and a 1–10 pain score.
   - **Deterministic rule-based triage**: emergency → 911 or ER; same day → urgent care or campus health; within 1–2 days → campus health or telehealth; routine → make an appointment. Every result states which rule triggered it. Danger words in the description (for example "chest pain" or "want to kill myself") raise a proactive alert; suicidal thoughts route to 988, poisoning routes to Poison Control.
   - Every option shows **the cost under the user's own insurance**. Missing fields are not guessed; the app tells the user where to look them up.
   - A local model explains the recommendation in the user's native language. The model **cannot change the triage level**.
4. **Find nearby places**: search Exa and Tavily for urgent care, ER, primary care or telehealth. **The user sees the query before it is sent.** Phone number, hours, and whether the user's insurer is mentioned are extracted locally from the results, each with the original excerpt and link.
5. **Visit preparation**: phone appointment script (English with a native-language translation side by side), an English condition card for the doctor (symptoms, medications, allergies, insurance, and "I need a free interpreter"), what to bring, and questions to ask the doctor.
6. **Bill / EOB explanation**: paste the text → extract amounts locally (charged, allowed, plan paid, you owe) → checklist: an EOB is not a bill; is the bill higher than the amount owed on the EOB; the No Surprises Act applies to out-of-network emergencies; request an itemized bill; ask about financial assistance → generate questions for the billing office. Runs entirely offline.
7. **Privacy proof page + disclosure ledger**: whether each field ever left the machine, every host contacted, blocked requests, no plaintext found in the vault file, and a static check proving only `egress.py` can make network requests. A "red-team button" also deliberately puts symptoms into a search request, showing live that DLP blocks the request.

## 3. Privacy design (the top judging criterion)

| Data | Leaves the computer? | Where to |
|---|---|---|
| City, state, ZIP | Yes (shown before sending) | Exa / Tavily, to find nearby places |
| Insurer name | User's choice | Exa / Tavily |
| Name, date of birth, member ID, group number | Never | — |
| Symptoms, description, history, medications, allergies | Never | — |
| Bill and EOB contents | Never | — |
| Triage, explanation, translation, bill explanation | Runs locally | Ollama (localhost) |

This also fixes the issues raised in the Unperson assessment: URLs are no longer exempt from DLP and are URL-decoded before checking; failed requests count as "possibly sent" in the privacy proof; redirects are disabled.

## 4. Reuse from Unperson

Reuse directly: the encrypted vault, the egress gateway (offline switch, allowlist, DLP, ledger), local model calls, the privacy proof, the static network check, localhost hardening (Host validation, custom header, CSP), the UI skeleton, and the test fakes.
Remove: OTP verification, data brokers, identity matching, removal requests, Sanity, Gradium.

**Reuse status (compared with `_src/unperson/app` at 17:30)**:

| Module | Origin | Notes |
|---|---|---|
| `textutil.py` | Unperson, unchanged | No changes |
| `codecheck.py` | Unperson, nearly unchanged | Static network-import check |
| `store.py` | Unperson, minor changes | AES-256-GCM vault with a new data shape |
| `egress.py` | Unperson, heavily changed | URL decoding before DLP, redirects disabled, failed requests recorded in the ledger |
| `llm.py`, `config.py`, `server.py` | Unperson skeleton, mostly rewritten | Local Ollama only; routes now serve care navigation |
| `benefits.py`, `navigation.py`, `catalog.py`, frontend | New | Calculations and UI for the three scenarios |
| `triage.py`, `bills.py`, `costs.py`, `places.py` | New drafts | **Not yet connected to the UI** |

**Done**: server, frontend, 28 tests (all passing), static network check, README; code pushed to GitHub.
**To do**: install Ollama; configure real Tavily/Exa keys; differentiate the demo data (all four providers currently show $25); decide whether to reconnect triage; video, interviews, Devpost copy.

## 5. Tracks

- **Primary: Privacy-First** ($2,500): healthcare is named in the track description, and the demo can run offline.
- **Secondary: Most Startup-able**: the users are at the venue; interview them tonight for evidence. The buyer hypothesis is the university's international student office or the student health plan. This is a hypothesis and must be labeled as one.
- **Surge is incidental only**: search is one feature, not the core of the product. Don't overstate it.

## 6. Schedule (EST)

| Time | Development | User validation (teammates in parallel) |
|---|---|---|
| Sat 16:30–19:00 | Finish server and audit; unit and end-to-end tests pass | Write the interview guide; find international students at the venue and on Discord |
| 19:00–22:00 | 5 frontend screens | Interview 5+ people and record their exact words (with consent, nothing invented) |
| 22:00–00:00 | Connect real Tavily/Exa keys, install Ollama, test in Chinese, fix bugs | Organize interviews, write the pitch |
| 00:00–01:30 | README, DEMO_SCRIPT, DEVPOST copy | — |
| Sleep | | |
| Sun 07:00–09:00 | Rehearse, record the 3–5 minute video, upload to YouTube | |
| 09:00–10:30 | Push to GitHub, submit on Devpost, check links and permissions | |
| 10:30–11:00 | Buffer | |

**Cut order** (when short on time, cut from the top down): bill explanation → telehealth search → Spanish templates → red-team button. The core path "triage → cost → find a place → visit prep → privacy proof" cannot be cut.

## 7. Demo video outline (about 4 minutes)

- 0:00–0:30 A real international student's struggle (with consent)
- 0:30–1:30 Enter symptoms → triage level, the rule behind it, and the cost under their own insurance → explanation in Chinese
- 1:30–2:15 Find a nearby urgent care: first show the query, then the results, original excerpts and links
- 2:15–3:00 Go offline → generate the phone script and doctor card, explain a sample EOB (clearly labeled as a sample) → the red-team button gets blocked
- 3:00–3:45 Interview evidence, first-customer hypothesis, limitations

## 8. Decisions needed from you

1. **Name**: is FirstVisit OK?
2. **Team**: how many people? Who builds and who does interviews?
3. **Languages**: templates in Chinese and English first (Spanish optional), with other languages left to the local model. OK?
4. **Environment**: **Ollama is not installed** on this Mac. We need to install `ollama` and download `qwen2.5:3b` (about 2 GB). Do we reuse Unperson's Tavily and Exa keys?
5. **Unperson**: keep it as a backup and not submit it, or submit both (need to check whether the rules allow it)?
