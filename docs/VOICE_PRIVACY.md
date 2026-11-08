# Browser dictation privacy boundary

Reviewed November 8, 2026. This is a capability and disclosure assessment, not a
promise about every browser vendor's processing or an independent network audit.

## What content is involved

Audio contains the spoken content itself. Sending audio to a recognition provider
already discloses that content, even if FirstVisit never sends the resulting text
through its own server or public-search gateway. HTTPS or an anonymous request ID
does not establish no retention, no training, no human review or end-to-end secrecy.

Ordinary Web Speech API recognition may use a server. The API does not expose one
uniform provider, retention duration, training opt-out, reviewer policy or deletion
mechanism that FirstVisit can verify and control. We therefore make no blanket
claim that browser-service dictation content is kept private, immediately deleted,
or excluded from model/service improvement. Other products' policies (for example
Google Assistant, Cloud Speech or Siri) cannot automatically be treated as the
contract for a website's Web Speech API session.

## Actual controls

- No microphone at page load. A supported browser exposes the optional control.
- Default mode requests on-device recognition with `processLocally=true` and checks
  `available({langs:[language], processLocally:true})`. It starts only when the browser
  reports the local language pack available. This is reliance on the browser API,
  not OS-wide verification. No automatic language-pack download or cloud fallback.
- Browser-service mode requires its own disclosure and an explicit Enable click.
  The disclosure covers spoken content, unknown/variable vendor retention and use,
  inability to delete vendor copies, and exclusion from the app gateway ledger.
- Browser-service mode is refused when this tab's app offline switch is on. The app
  switch is not a browser/OS firewall; it cannot globally isolate a browser service.
- Results append to the current input, are editable and never auto-submit. Final
  results use `resultIndex` to avoid re-appending prior utterances. No audio backend,
  `MediaRecorder`, audio file storage or audio upload is implemented in FirstVisit.
- Navigation, locking, hiding/leaving the page or changing dictation settings aborts
  the recognizer. User denial, errors and absent local support keep typing available.
- FirstVisit retains only a count of explicitly enabled browser-service attempts in
  tab memory, not audio, audio-derived content logs or a claimed network observation.
- The transcription stays in the draft until submitted. Submitted task goals and
  confirmed report facts are saved in the encrypted local vault. Browser history
  receives opaque route IDs only, not draft health content.

## Sources and limits

- [MDN: SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)
- [MDN: processLocally](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally)
- [MDN: on-device availability and language packs](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API/Using_the_Web_Speech_API)
- [Microsoft: on-device recognition](https://learn.microsoft.com/en-us/microsoft-edge/web-platform/speech-recognition-api)
  documents a specific Edge implementation and its availability; it is not a policy
  for Chrome, Safari or all browsers exposing the same API.
- [Apple: Siri, Dictation & Privacy](https://www.apple.com/legal/privacy/data/en/ask-siri-dictation/)
  describes conditional on-device/server behavior, default audio storage and opt-in
  improvement processing. It does not establish a universal website API retention rule.

Recognition behavior is covered by fake-browser unit checks. Real microphone,
permission prompts and provider network/retention behavior require a browser/device
acceptance pass and are not established by those checks or the app's gateway ledger.
