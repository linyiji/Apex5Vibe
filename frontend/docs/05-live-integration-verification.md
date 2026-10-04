# Apex5Vibe English PC Web Live Integration Acceptance

Date: **2026-10-04** (Asia/Hong_Kong). Executed locally against the real FastAPI backend, SQLite, and TeamRouter **gpt-6.1-sol**. Frontend mode: **Live**. No GitHub upload or deployment was performed.

The final English demo uses `runtime/english-demo/`. Earlier backend and Chinese-language integration records remain in the original `runtime/` directory. AI histories were preserved rather than rewritten or translated after the fact.

## Results

| Scenario | Observed outcome |
|---|---|
| Case 1 PDF initial assessment | **5 / LOW**, eligible, **GBP 6,400.00** indicative advance |
| Case 2 PDF initial assessment | **35 / HIGH**, manual review, no automatic advance |
| Case 2 Errors.xlsx | **50 / HIGH**, integrity **15 / 15** |
| Case 2 Corrected.xlsx with explicit replacement | **35 / HIGH**, integrity **0 / 15** |
| Correction banner | **Risk decreased by 15 points: 50 → 35 · HIGH → HIGH** |
| Other six Case 2 modules | Same Run IDs and one run each throughout both evidence uploads |
| Main Case 2 invoice | GBP 50,000.00 throughout; original PDF download SHA-256 unchanged |
| Evidence history | Errors superseded, Corrected active v2; both files remain downloadable |
| AI input after correction | Contains the active corrected sheet only, not the superseded erroneous sheet |

Current cases:

- Case 1: `case_985c88465a2d45128164ff6b474fcdf4` — [open locally](http://127.0.0.1:3000/assessment/case_985c88465a2d45128164ff6b474fcdf4).
- Case 2: `case_ce305ab264ac40429f8b7b5a4c3d14c9` — [open locally](http://127.0.0.1:3000/assessment/case_ce305ab264ac40429f8b7b5a4c3d14c9).

The final English run used **17 successful real AI module executions**: Case 1 seven initial modules plus one payment rerun, and Case 2 seven initial modules plus two integrity reruns. Requested and reported model names are gpt-6.1-sol. All returned summaries and findings were checked for English output. Structured evidence, provider IDs, token usage, scores, and invariants are in [the acceptance record](../../docs/validation/frontend-live-acceptance.json). Full English JSON examples are in [contracts/examples/english](../../contracts/examples/english/).

## Browser behavior verified

- Actual PDF bytes upload, parsed invoice data, server-backed PDF preview, and original download integrity.
- Initial real job progress and automatic Step 3 → Step 4 navigation without an extra result button.
- Independent file uploads and reruns; choosing a file alone leaves the score unchanged.
- Explicit replacement checkbox: submitting Corrected without confirmation shows an English error and keeps the score at 50; confirmed replacement proceeds.
- Supplementary English text and Save only: the target becomes stale, current financing is Pending, and the previous score is historical.
- Manual adjustment: AI 5 + manual -5 = final 0 while the original AI output remains. A new AI run restores AI 5 and marks the previous adjustment pending_review; financing stays Pending until the analyst confirms a new adjustment of 0.
- Full view, source citations, immutable run inputs, evidence versions, notes, adjustment history, and state events.
- Low/High queue filtering, opening saved cases, and result recovery after page refresh and switching to the production server.
- English UI, generated findings, error copy, and upload controls. No visible Chinese text in the final result screens.
- 1440×1000 and 1280×900 desktop viewports: document width equals viewport width, with no horizontal overflow.
- No uncaught browser runtime errors in the checked flows. Intentional failed network requests were part of connection testing.

Earlier in the same integration session, before the English data separation, Existing/Manual company conflicts were tested through the UI, including blocked assessment and explicit resolution. A real needs_info response settled to the result page with Pending and no advance. Aborting backend traffic preserved the note draft, disabled writes, and did not activate Mock mode; reconnection restored polling. An empty upload was rejected before any write.

A real model run initially misread the optional field-sheet requirement and the provenance of parsed entity facts. The prompt was corrected to state that main-PDF facts are already supplied and the supplementary sheet is optional. The final two English initial assessments succeeded from their PDFs without requiring a sheet. Earlier failed runs remain in the separate historical database.

## Build and backend checks

| Check | Result |
|---|---|
| Backend pytest | **27 passed**, 0 failed |
| Ruff check and format | Passed |
| Runtime OpenAPI export check | Passed |
| Generated frontend API types | Passed, openapi-typescript 7.13.0 |
| Frontend ESLint | Passed |
| TypeScript / Next route types | Passed |
| Next.js production build | Passed |
| Production browser smoke at port 3000 | Passed; persisted Case 1/2 outcomes restored |

One dependency deprecation warning remains in offline tests: Starlette TestClient reports its future httpx2 migration. It did not fail a test. GitHub CI configuration is prepared locally but has not been run remotely.

## Screenshots

- [English production homepage](screenshots/live/en-production-home.png)
- [Case 1: Low result](screenshots/live/en-production-case1.png)
- [Case 2: risk decreases from 50 to 35](screenshots/live/en-case2-risk-decrease.png)
- [Case 2: complete English module detail](screenshots/live/en-case2-full-view.png)
- [Case 2: production result at 1280px](screenshots/live/en-production-case2-1280.png)
- [Payment history and adjustments](screenshots/live/en-payment-full-view.png)

The final naming update to **Apex5Vibe** was verified in the page header, browser title, and API title. Homepage and production-result screenshots above show the final name. Earlier scoring-transition captures are retained unchanged as evidence from before that naming update.

## Verification limits

Desktop Chromium was tested; Safari, Firefox, mobile, and a dedicated accessibility audit were not. Backend concurrency/idempotency and 409 behavior are covered by offline tests. The frontend preserves drafts on its 409 branch, but a separate browser-specific 409 recovery test was not completed; the attempted cross-origin response interception instead exercised connection-error handling and was removed.

This is the supplied two-case local demo, not a general invoice/OCR service, production security review, or calibrated lending model. Original evidence and user-entered notes are preserved in their submitted language. Historical prototype documents and earlier acceptance JSON remain labeled as history; they do not describe the final English Live UI.
