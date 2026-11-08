# FirstVisit — submission copy draft

Not submitted. Hack1984 deadline: Nov 8, 2026, 11:00 AM EST. Track: Privacy-first. A demo video is required for judging.

## Tagline

A private care navigator for people new to US healthcare.

## Inspiration

Arranging a visit involves more than searching for a doctor: people need to understand benefits, compare supported costs, ask the right questions and remember what happens next. Those steps can involve health details that should not need to be sent to a cloud assistant.

## What it does

FirstVisit keeps an encrypted local health profile and helps adults prepare for non-emergency care. It distinguishes insured, uninsured and choosing-plan needs; organizes a sourced shortlist; lets people bring back candidates from external directories; and records dated replies about appointments, language support, referrals and service-specific quotes. Confirmations update the comparison, while missing and stale evidence stays explicit. Saved journeys and visit outcomes support the next action.

The initial example uses an illustrative Northeastern student near Brookline 02445 and real clinic-location sources. Published plan references are separate from member-specific inputs. The official page links older benefit documents, so the app does not treat them as verified current-year copays. No exact physician network or appointment availability is claimed without confirmation.

## How we built it

Python local HTTP server, vanilla JavaScript UI, AES-256-GCM encrypted vault with scrypt key derivation, local SBC text/PDF extraction, deterministic cost arithmetic and a single outbound gateway. Tavily and Exa returned public provider-search leads in a synthetic Brookline acceptance run; this does not verify provider claims. A local Ollama model (`qwen3.5:2b`) translates the fixed call script into the user's language on-device, with Wi-Fi off. It never receives health history and cannot change costs or safety rules. When free-form drafts invented facts in testing, we limited the model to line-by-line translation with a labeled template fallback.

## Privacy evidence

App-mediated requests pass through destination checks, disclosure controls, offline blocking, a private-value filter and a ledger. A synthetic self-check exercises gateway preflight without a network call. A separate receiver observes a test app process using synthetic data, including blocked sensitive requests, failed requests, refused redirects and offline behavior. This does not establish OS-wide process isolation or a full security audit. External websites have their own privacy practices.

## Challenges and limits

A clinic website is not exact-plan network confirmation. A benefits document is not a clinic quote. The prototype preserves unknowns rather than inventing prices or appointments. It does not diagnose, automatically book, verify insurance eligibility or provide clinically validated triage.

## What we learned

Engineering observation: the useful workflow is not just a ranked list; it is collecting evidence, resolving uncertainty and retaining the next action. Whether intended users find this useful and whether an organization would pay are hypotheses still requiring actual research.

## Next steps

Collect target-user observations and real provider/insurer confirmations; expand service and directory coverage only where supported.

## Publication fields to finish

- Repository URL and access: verify after intended changes are committed/pushed.
- Video URL: recording/upload pending; use DEMO_SCRIPT.md.
- Team names/roles and asset credits: user-supplied details required.
- Track selection: Privacy-first. Tavily/Exa live search was tested with synthetic inputs (see STATUS.md); don't claim more than that.
- User quotes, traction and customer claims: add only with evidence and consent.
