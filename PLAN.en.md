# FirstVisit — Pivot Plan (draft, pending confirmation)

> English version of [PLAN.md](PLAN.md). This is a translation of the 15:54 EST draft. It does not include later code progress.

> Deadline: Sunday, 2026-11-08, 11:00 AM EST. It is now about 4 PM Saturday, leaving about 19 hours, which must also cover sleep, recording the video, and submitting.

## 1. One-line positioning

**FirstVisit: helps international students know where to go, how much it will cost, and what to say for their first doctor visit in the US. Health and insurance information stays on their own computer.**

- **Target user**: international students getting care in the US for the first time, starting with Northeastern University and its student health insurance plan.
- **Pain points**: they can't tell the ER, urgent care, the campus health center, and telehealth apart; they don't know what copay or in-network means; making an appointment by phone in a second language is stressful; they receive a bill or an EOB they can't understand and don't know whether to pay it.
- **How we differ from competitors**: Docus, Guava and ChatGPT Health interpret labs and medical records; Zocdoc books doctors. We guide the process before and after a visit, and our privacy can be proven: the search service only learns that "someone near 02115 is looking for urgent care", not why.
- **Out of scope**: diagnosis, lab interpretation, medical-record integrations, automatic booking, and healthcare systems outside the US.

## 2. MVP demo flow (5 screens)

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

**Drafted (untested)**: `config.py`, `store.py`, `egress.py`, `triage.py`, `costs.py`, `places.py`, `bills.py`, `llm.py`
**To write**: `server.py`, `audit.py`, frontend, tests, docs

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
