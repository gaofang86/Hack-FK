# FirstVisit — submission copy draft

Not submitted. Hack1984 deadline: Nov 8, 2026, 11:00 AM EST. Track: Privacy-first. A demo video is required for judging.

## Tagline

A private care navigator for people new to US healthcare.

## Inspiration

Arranging a visit involves more than searching for a doctor: people need to understand benefits, compare supported costs, ask the right questions and remember what happens next. Those steps can involve health details that should not need to be sent to a cloud assistant.

## What it does

FirstVisit keeps an encrypted local health profile and helps adults prepare for non-emergency care.

- **Four ways in:** Stay healthy (a regular doctor, checkups, preventive care), Get care (a new concern, where to go, how booking works), Manage my care (follow-ups, refills, reports, unfinished tasks) and Insurance & costs. If you just type a sentence, deterministic rules suggest the matching category; symptom wording always goes to the safety check first.
- **Coverage first:** every care task opens with "Step 1 · Coverage & costs" (insured, uninsured, choosing a plan, or unknown) before preparing or finding care, so questions and costs match the person's situation. Preparation material is generated in the selected interface language (English or Chinese) and tailored to that coverage situation.
- **Find by need or by name:** follow the guided flow, or search a sourced local directory of Boston/Brookline primary-care practices and officially profiled clinicians by doctor, clinic or street. The lookup runs on-device and sends nothing.
- **Get there and book:** each clinic with a specific street address has a Google Maps directions link (address only). An "Book online" link appears only when the official page links an online scheduling page; opening it is not a booking.
- **Close the loop:** a sourced shortlist, candidates brought back from external directories, and dated replies about appointments, language, referrals and service-specific quotes update the comparison. Missing and stale evidence stays explicit. Saved tasks and visit outcomes support the next action.

The initial example uses an illustrative Northeastern student near Brookline 02445 and real clinic-location sources. Published plan references are separate from member-specific inputs. The official page links older benefit documents, so the app does not treat them as verified current-year copays. No exact physician network or appointment availability is claimed without confirmation.

## How we built it

Python local HTTP server, vanilla JavaScript UI (English/Chinese), a small sourced directory (official health-system, clinic and clinician pages checked 2026-11-08), AES-256-GCM encrypted vault with scrypt key derivation, local SBC text/PDF extraction, deterministic cost arithmetic and a single outbound gateway. Tavily and Exa returned public provider-search leads in a synthetic Brookline acceptance run; this does not verify provider claims. A local Ollama model (`qwen3.5:2b`) translates the fixed call script into the user's language on-device, with Wi-Fi off. It never receives health history and cannot change costs or safety rules. When free-form drafts invented facts in testing, we limited the model to line-by-line translation with a labeled template fallback.

## Privacy evidence

App-mediated requests pass through destination checks, disclosure controls, offline blocking, a private-value filter and a ledger. A synthetic self-check exercises gateway preflight without a network call. A separate receiver observes a test app process using synthetic data, including blocked sensitive requests, failed requests, refused redirects and offline behavior. This does not establish OS-wide process isolation or a full security audit. External websites have their own privacy practices.

## Challenges and limits

A clinic website is not exact-plan network confirmation. A benefits document is not a clinic quote. The prototype preserves unknowns rather than inventing prices or appointments. It does not diagnose, automatically book, verify insurance eligibility or provide clinically validated triage.

## What we learned

Engineering observation: the useful workflow is not just a ranked list; it is collecting evidence, resolving uncertainty and retaining the next action. Whether intended users find this useful and whether an organization would pay are hypotheses still requiring actual research.

## Next steps

- Expand the sourced directory and add current-year plan benefits as insurers publish them.
- A local conversational entry (on-device model) on top of the deterministic routing, once the flow is stable.
- Sessions with international students to validate the need; distribution through universities and student plans is a hypothesis to test.

## Publication fields to finish

- Repository URL: https://github.com/gaofang86/Hack-FK (all changes pushed to main; confirm it is public before submitting).
- Video URL: recording/upload pending; use DEMO_SCRIPT.md.
- Team names/roles and asset credits: user-supplied details required.
- Track selection: Privacy-first. Tavily/Exa live search was tested with synthetic inputs (see STATUS.md); don't claim more than that.
- User quotes, traction and customer claims: add only with evidence and consent.
