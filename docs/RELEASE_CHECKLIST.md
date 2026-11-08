# Release evidence and handoff

Use PLAN.md acceptance criteria and verification reports. A prepared document is not an executed external action.

## Automated and local

- Run `python3 -m unittest discover -q`, `python3 scripts/audit_egress.py`, `node --check static/app.js`.
- Run `python3 scripts/verify_privacy.py --out verification/privacy-receiver.json` for separate-process receiver observation.
- Run `python3 scripts/verify_ollama.py --out verification/ollama.json` with Ollama running (Wi-Fi off to record no network route).
- Run `python3 scripts/verify_install.py` for a fresh temporary source copy, venv, dependency install, tests and checks. It needs package download access and local listener permission.
- Browser rehearsal: real-source NEU scenario, external candidate, answer, quote, saved recovery, unavailable candidate, offline preparation and privacy self-check. Use fictional personal data.

## Evidence still requiring outside participation

- Current-year NUSHP SBC/benefit description and exact clinician/location network confirmation.
- Real service-scoped quote, new-patient acceptance and appointment availability.
- Intended-user sessions using USER_VALIDATION.md, with actual observations.
- Live Tavily/Exa search acceptance passed with synthetic Brookline inputs; see STATUS.md. Local-model acceptance: see verification/ollama.json.

## Submission

- Deadline: Nov 8, 2026, 11:00 AM EST (Hack1984). Team required; projects without a demo video are not judged.
- Review scope, README, demo and DEVPOST_DRAFT.md for claims matching evidence.
- Record video using DEMO_SCRIPT.md; verify captions, audibility and that no secrets or patient information appear.
- User must supply team details and review any participant permissions.
- Commit/push the intended code, check repository access, upload video and verify public links before submission.
- Record the submission receipt. No submission, contact, interview or upload is performed by these documents.
