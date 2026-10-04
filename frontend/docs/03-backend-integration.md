# PC Web Backend Integration

Date: 2026-10-04. Stack: Next.js + local FastAPI / SQLite + TeamRouter gpt-6.1-sol. UI, generated assessment text, and API errors are English. The original preparation checklist is preserved in [the archive](archive/03-backend-integration-plan.md). Executed checks are recorded in [Live acceptance](05-live-integration-verification.md).

## Runtime contract

- `contracts/openapi.json` in the repository root is the runtime contract. `npm run generate:api` generates TypeScript with openapi-typescript 7.13.0. The archived four `/api` endpoints are not used by Live.
- Modules: invoice_integrity, buyer_verification, seller_verification, relationship, market_price, payment_history, duplicate_financing. Higher scores mean higher risk; LOW < 30, HIGH ≥ 30.
- Completeness is the number of current successful modules out of seven. Amounts are server decimal strings; the frontend formats them and never calculates financing offers.
- Live is the default. Explicit Mock mode only preserves the original prototype. Network failures, AI failures, or missing data never generate a simulated successful result.
- The invoice entry accepts the supplied PDF form. Evidence supports text PDF, XLSX, and CSV, subject to capabilities (20 MiB/file, 10 files/request). OCR, images, Word, and legacy XLS are unavailable.
- Extracted invoice fields are read-only. Correction uses a replacement PDF; there is no invented general-purpose invoice PATCH.

## Request and state flow

The upload page loads capabilities and companies in parallel. The queue is fetched independently. Submission creates a case, uploads actual PDF bytes, then opens the URL containing the server case_id. Review and document preview use Workspace and file_id; they survive browser refresh without sessionStorage.

Buyer/Seller support Skip, Existing, and Manual. A company conflict disables the initial assessment until **Use invoice buyer/seller** explicitly resolves it through PATCH parties. Skip still identifies and links the invoice company.

POST assessments returns an asynchronous job. Workspace polling runs approximately every 800ms while work is active and every 2.5s otherwise. Navigation cancels polling; older case revisions are discarded. The UI automatically opens Step 4 when `initial_assessment_status=settled` and `navigation.target=result`, including failed or needs_info results. Module reruns remain on Step 4.

When `aggregate.current_result` is null, the UI shows Pending, labels last_valid_result as historical, and hides a current financing amount. Stale modules label their old score. Pending manual adjustments require reconfirmation. Score changes distinguish increases, decreases, and unchanged results; Case 2 correction displays **Risk decreased by 15 points: 50 → 35**.

## Writes and evidence replacement

Each logical action has a UUID Idempotency-Key and the latest expected_case_revision or expected_module_version. A transport retry reuses the same key/body. A 409 triggers a refresh while preserving the user's draft; the client never blindly replays with a newer version.

- **Save only:** persist evidence/information and invalidate the affected module, without running AI.
- **Send & reassess:** rerun that module. Other modules retain their current Run IDs.
- **Files and text together:** upload files with rerun=false; read the latest module version; then save the note with rerun=true. These are two transactions. If the note fails after file acceptance, the UI explicitly says the files are saved and retains the note draft.
- **Invoice field sheet:** a single XLSX in Invoice Integrity defaults to the versioned group. General evidence can be selected instead. With an active sheet, the user must explicitly check Replace current field sheet to send its supersedes_evidence_id. Without that choice, submission is blocked.
- The new sheet remains pending until parsing succeeds, then atomically replaces the old sheet. Full view shows active/pending/failed/superseded versions. Historical files and runs remain accessible.
- **Manual adjustment:** persist requested/effective values, reason, and current applies_to_run_id. Positive raises risk; negative lowers risk. A new AI run requires reconfirming the previous adjustment.

## Full view and recovery

Full view contains the AI summary, findings, citations, evidence versions, notes, adjustments, runs, and state events. Selecting a historical run exposes its immutable input/output and provider metadata; current manual/final values are clearly labeled separately. Files download from the backend.

The queue is persisted and supports Low/High filtering, pagination, and refresh. Historical risk is labeled Previous result. A disconnected case retains its last displayed state and drafts while writes are disabled. Reconnection resumes polling. Earlier Chinese-language test data is retained in the original runtime directory; the current demo uses a separate English database with fresh real AI runs.

## Configuration and limits

Frontend: `http://127.0.0.1:3000`. Backend: `http://127.0.0.1:18080`. Backend CORS configuration allows both localhost:3000 and 127.0.0.1:3000. NEXT_PUBLIC variables contain no TeamRouter credentials.

This is a local desktop demo with synthetic local references and a fixed analyst identity. General OCR, multi-tenant authentication, external registry checks, actual financing execution, mobile adaptation, and production deployment are outside scope. Work has not been uploaded to GitHub.
