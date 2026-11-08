# FirstVisit — demonstration script

Purpose: show a private, persistent care-navigation workflow. Target: roughly 4 minutes. This is a script, not a claim that a video has been recorded or submitted.

## Prepare

Start Ollama with `qwen3.5:2b` pulled. Run `python3 run.py --preview` and open http://127.0.0.1:8767. Use fictional personal information only. This disposable preview has no search keys and does not idle-lock. Identify it on screen. Have the receiver and installation reports ready. Do not show `.env`, member IDs or real health records.

## 0:00–0:30 — Problem and promise

“Someone new to US healthcare may know they need a follow-up but still need to work out where to go, how their plan applies and what to confirm. FirstVisit keeps their private health profile locally and helps them work through that task.”

Do not present a fictional character as an interview participant.

## 0:30–1:15 — A clearly labeled NEU / 02445 scenario

Create a fictional adult profile. On home choose **Explore NEU / 02445**. Confirm the planned follow-up, insured branch and ZIP. Explain that the scenario does not overwrite the saved personal profile.

Proceed through the query review using the local directory. Show two real clinic location sources. Explain the 2026–27 public reference: annual period and annual fee; neither establishes the individual's active coverage. Open the warning that linked benefit PDFs are 2025–26. No current-year copay is claimed.

## 1:15–2:05 — A shortlist that makes uncertainty actionable

Show **Supported cost comparisons** versus **Options needing confirmation**. Unknown is not free. Show the official insurer-directory handoff and instructions for checking the exact clinician and address. Do not say either clinic is already confirmed in-network.

Choose **Add a provider you found**. For a demonstration-only extra candidate, use `Example test practice`, `Fictional address — not a real clinic`, and `https://example.org/clinic`, with a source description that explicitly says fictional. It should remain unconfirmed, not become a supported recommendation.

## 2:05–2:50 — Record answers and continue

Choose **Record office reply** on the fictional extra candidate. Enter a clearly synthetic response and source. Show how a known answer leaves the outstanding-question list; unknown answers remain open. Show a negative availability reply keeps the candidate as a backup.

Use **Add quote / confirmation** only for a clearly labeled synthetic quote in this rehearsal, not as evidence from a real clinic. To show price reranking without mixing evidence, use the separate **Explore a fictional example** path. State the mode change out loud.

Open **Prepare this visit** and show the selected provider's name, address and outstanding questions as a built-in template. Choose **Use my local model**: each English line now has a Chinese line under it, labeled `local model (qwen3.5:2b)`. Say that the model only translates fixed questions on this laptop; it never sees health history or changes costs. Return home and continue the saved journey.

## 2:50–3:30 — Privacy and offline operation

Open **Privacy**, keep offline mode off for the first self-check, and choose **Run synthetic privacy self-check**. Show the DLP block and ledger. The phrase is made up and no network call is made by this self-check.

Turn offline mode on, then **turn Wi-Fi off on camera** (show the menu bar). Reopen the saved journey and choose **Use my local model** again: it still works. Turn Wi-Fi back on afterwards. Show the independent receiver report: public controlled search reached the receiver, sensitive URL/header/body attempts did not, redirects were not followed, offline requests were not received. Explain that this is controlled local observation, not OS-wide isolation or live API certification.

## 3:30–4:00 — What exists and what remains

“Local profiles, task continuity, candidate intake, dated confirmations and deterministic comparisons work. Real sources are separated from fictional demonstration data. Exa and Tavily were tested with a synthetic public query, and the local model translates call scripts with Wi-Fi off. Current-year NUSHP cost sharing, exact physician network and real appointment availability still need confirmation.”

Show user-test findings only after actual trials. Otherwise say user validation is pending. Do not claim completed bookings, savings, paying customers or clinical validation.

## Unified homepage demonstration

1. Start `python3 scripts/start_local_demo.py` and open localhost:8768. First show
   that a person without a report can create a first-visit task, prepare questions,
   and proceed to the existing care intake without completing an entire profile.
2. Create a separate report-preparation task. Select the locally held redacted demo
   PDF, review its extracted rows, and confirm. Keep the raw source outside the repo.
3. Show the task goal, linked report, personal clinician note and separate booking
   questions. Finding care continues the same saved task rather than replacing it.
4. Show the query disclosure and app gateway privacy view. Never present zero gateway
   requests as proof of zero browser voice traffic or OS-wide isolation.
5. Optional dictation: on-device requires installed browser support; otherwise type.
   Browser-service recognition needs the separate disclosure and explicit consent.
   State that spoken content can leave and vendor retention/use cannot be guaranteed.
   Do not narrate a real microphone/browser pass unless it was actually observed.
