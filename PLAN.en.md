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

### Local text-agent implementation update (2026-11-08)

The first text stage is implemented: deterministic task/cost reads, local structured
Ollama routing, quoted office-reply proposals, explicit review, and saved-fact ranking
updates. Real synthetic-model evidence is recorded in `verification/agent-local.json`.
Call-script translation and live public search have separate acceptance evidence in
STATUS.md. This text-agent stage does not include microphone/transcription/playback
or verification of real provider prices, appointments or exact insurance participation.
See README for setup and STATUS for each verification scope.

Merge compatibility: call-script translation uses `OLLAMA_MODEL` (default
`qwen3.5:2b`); structured office-reply extraction uses `OLLAMA_AGENT_MODEL` (default
`qwen2.5:3b`). The local qwen3.5 runtime refused JSON-schema output during merge
acceptance. Both routes remain local and their configuration is independent.

### Unified intake extension

A report is optional evidence in the shared care-task lifecycle, not a separate
product or mandatory starting point. The homepage accepts typed goals and optional
browser dictation before directing first-visit, concern, report and follow-through
scenarios into the same task structure. Full medical profiles are not prerequisites.
Report facts require review; they do not create medical conclusions or orders.

Optional browser-service dictation is an explicit exception to the default local
input-processing boundary: audio already contains spoken content, may leave through
the browser's service, and provider retention/use/deletion is not controlled by the
app. On-device mode never silently falls back. See `docs/VOICE_PRIVACY.md` and STATUS
for actual implementation, evidence and unresolved real-browser acceptance.

## 10. Product structure (updated 2026-11-08)

This section records today's product decisions in business terms. Implementation evidence belongs in STATUS.md.

### Two questions, asked in order

Every care task answers two separate questions:

1. **What do you want to get done?** Four starting points: **Stay healthy** (a regular doctor, checkups, preventive care, first time in US healthcare), **Get care** (a new concern, where to go, how booking works), **Manage my care** (a follow-up or test a clinician suggested, refills, reports and visit records, unfinished tasks) and **Insurance & costs** (using a plan, care without insurance, comparing ways to pay, asking for prices; bills come later). A person can also just describe the situation; the product suggests the matching starting point, and anything that sounds like a symptom goes to the safety check first.
2. **How will you pay?** The three scenarios in §3 (insured, uninsured, choosing a plan). This is asked **once, before** preparing or finding care, because it changes which costs and questions apply.

### One path per task

Each task follows one visible line, and the person can always see where they are and what comes next:

- **Insured / uninsured:** your need → coverage & costs → choose a clinic → contact & confirm → after the visit.
- **Choosing a plan:** your need → coverage & costs → compare plans → enroll through official channels → then find care. This path does not send people through clinic search (§3).
- If coverage is unknown, later steps wait until it is answered. A question already answered is not asked again.

A short "what we know" summary stays beside the path: what is confirmed, what is unknown (never shown as $0), and the next step in that scenario's own words.

### Two ways to find care, and the handoff

People arrive either with a need or with a name (a doctor or clinic a friend, school or insurer mentioned). Both are supported: **by need** through the guided flow, or **by name** in a sourced local directory. Each clinic with a specific street address offers directions; an online booking link appears only when the official page provides one. Opening a booking link is not a booking; the person books externally and records the outcome.

### The role of AI: rules decide, the local model explains

Facts, safety triage, costs, coverage status and ranking are decided by fixed rules. A local, on-device model may turn those settled facts into a plain-language explanation for this person (for example what "cost unknown" means for them, or what to ask a clinic). It may not add facts, numbers, coverage or network claims, guesses about why something ranks first, or diagnoses. If its explanation adds anything that is not supported, the product shows the rules-based wording instead. The product remains fully usable without a model.

### Evidence used as reference

Published plan figures from a prior or unstated year may be shown as a clearly labeled reference ("prior-year reference, confirm for this year"), never as a current cost. The sourced provider directory is a core asset: it grows only from official pages, and each entry states what remains unconfirmed.

### Additional acceptance criteria

| ID | Observable pass condition |
|---|---|
| G10 Continuous path | At any point in a task, the person can name the current stage and next step; coverage is asked once; choosing a plan never requires clinic search |
| G11 Explained, not invented | Model explanations introduce no fact, number or claim absent from the rules output; unsupported output falls back to rules wording; the task works without a model |
| G12 Find and get there | A person can find a sourced clinic by need or by name, open directions, and see an official booking link only where one exists, without the product claiming a booking |
