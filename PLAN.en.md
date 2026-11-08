# FirstVisit — Product goals and acceptance criteria

English counterpart of [PLAN.md](PLAN.md). This document defines intended outcomes, not implementation history. Current evidence and next work belong in [STATUS.md](STATUS.md); setup and usage belong in [README.md](README.md).

## 1. Goal

Help adults unfamiliar with US healthcare make and act on an evidence-supported, non-emergency care decision using their needs, insurance, budget and preferences. Keep private health information on the device by default, and use user-confirmed visit outcomes to support the next action.

Start with international students and newcomers in Boston, without requiring school or student identity. Location finds options; insurance determines payment pathways; neither replaces the person's current health need.

## 2. Successful user outcomes

After a session, the user can explain their task, whom to contact first and why, which costs are supported versus illustrative or unknown, what to confirm and with whom, and how to save the outcome and continue. Success means progress toward care, not the number of generated explanations or listed providers. Do not promise the globally cheapest provider, objectively best clinician or unverified appointments.

## 3. Three entry points

| Situation | First task | Outcome |
|---|---|---|
| Insured | Understand relevant benefits and confirm the exact plan, service and location | Supported payment scenarios, comparable options and outstanding questions |
| Uninsured | Check possible existing coverage and explore self-pay and assistance | Supported comparison or an actionable quote request; eligibility remains unconfirmed |
| Choosing insurance | Identify expected needs and compare candidate plans | Premium-plus-use scenarios with unknowns visible; enrollment through official channels |

Do not force all situations through provider search. The health profile reduces repeated input, supports relevant reminders and retains visit feedback. Every collected field needs a purpose and must be correctable and deletable.

## 4. Care-task loop

Clarify need → confirm relevant profile and benefits → collect candidates and evidence → compare sufficiently supported options → resolve questions → update costs and ordering → user books externally and records confirmation → record visit outcomes and follow-up tasks.

Separate comparable options from leads needing confirmation. Unsupported leads receive no best-option label. For missing information, explain the gap, its effect, whom to ask and the exact question. Apply recorded answers only to the matching provider, location, service and plan. Opening a booking link is not a booking; profile updates require user review.

## 5. Constraints

### Evidence and costs

Distinguish search leads, provider publications, user confirmations and fictional examples. Important facts retain source, date and scope. Unknown is not zero; an insurer mention is not exact-plan participation; opening hours are not appointment availability. Separate plan benefits, network evidence, service charges and personal estimates. An SBC is not a provider quote.

Use deterministic cost calculations with explicit assumptions, inclusions and exclusions. The local model cannot change amounts or certify coverage. Explain ranking inputs and missing evidence. Sourced patient reviews are not clinical quality scores.

### Safety and privacy

No diagnosis, medication advice or medical clearance. Absence of a rule trigger does not establish that waiting is safe. Emergency warnings never depend on price comparison or insurance intake.

Keep profiles, symptoms, history, medications and private notes local by default. Models use local services only, with no cloud fallback. Before app-mediated transmission, display the actual query, recipients and fields. Queries may reveal location, care type and authorized insurance information; do not describe disclosure as location only. Explain external website handoffs separately. Gateway logs do not prove system-wide network isolation.

Support encryption, locking, correction, per-item deletion and complete erasure.

## 6. Delivery boundary

Boston adults seeking non-emergency primary care or clinician-directed follow-up. Retain existing same-day warnings and entry points without claiming clinically validated triage. Support a clearly bounded real provider set and benefit structures, including cash and unknown branches. Support one verifiable SBC text/PDF extraction workflow with review of important fields, not arbitrary document recognition.

Retain local profiles, relevant refill/follow-up reminders, visit records and preparation materials. Clearly label templates when no local model is available. Defer full bill/EOB workflows, nationwide coverage, arbitrary image OCR, automatic booking, live insurer integrations, complete hospital episode pricing and autonomous medical advice.

## 7. Acceptance criteria

| ID | Observable pass condition |
|---|---|
| G1 Real path | One complete preparation path supported by real sources; no invented replacement for missing quotes |
| G2 Personalization | Changing private preferences or confirmed benefits for the same candidates changes results deterministically and explainably |
| G3 Confirmation loop | Missing evidence leads to specific questions; saving answers updates the matching comparison; unconfirmed options remain visible |
| G4 Cost integrity | Benefits, quotes, examples and unknowns remain distinct; stale, missing or mismatched evidence does not produce false precision |
| G5 Continuity | Saved tasks can resume; user-reviewed visit outcomes create relevant follow-up tasks |
| G6 Offline use | Saved profiles, materials and scripts remain available offline; live search clearly requires connectivity |
| G7 Inspectable privacy | Demonstrate disclosure preview, a blocked sensitive request and the ledger; separately describe gateway tests and external network observations |
| G8 Comprehension | Intended users can state their next action and distinguish estimates, examples and unknowns; record observed failures without fabricated feedback |
| G9 Delivery | Verify fresh setup and the browser flow; demo and submission accurately distinguish real, manual and fictional components |

## 8. Validation direction

Test whether users can complete their next step before testing repeat use and willingness to pay. Universities and student insurers are potential distribution and buyer hypotheses. Local processing, inspectable cost scenarios and persistent tasks are a combination to validate, not proof that competitors or general assistants cannot provide it.


## 9. Integration goals and acceptance

Current implementation and validation evidence belongs in [STATUS.md](STATUS.md). These criteria define the target evidence for the integrations.

| Integration | Goal | Acceptance criteria | Available fallback |
|---|---|---|---|
| Ollama local model | Produce reviewable preparation drafts, including Chinese, on-device | Install runtime/model; verify loopback calls, Chinese output, offline use and failure fallback; no changes to safety rules or cost math, no cloud fallback | Clearly labeled built-in templates |
| Tavily / Exa search API | Discover public provider leads inside the app | Configure at least one API key in local `.env`, never version control; verify real NEU / 02445 results, disclosure preview, ledger, failures and offline handling | Sourced local directory, external lookup links and manual candidate entry |

An API key authenticates a search service; it is not member insurance information. Search discovers leads, not verified diagnoses, prices, exact-plan participation or appointments.
