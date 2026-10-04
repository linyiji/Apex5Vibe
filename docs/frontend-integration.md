# Frontend API Integration

The PC Web frontend is now implemented in `frontend/`. It uses the real FastAPI `/v1` contract and TeamRouter gpt-6.1-sol. See [implementation and state flow](../frontend/docs/03-backend-integration.md) and [browser acceptance](../frontend/docs/05-live-integration-verification.md).

The runtime source of truth is `contracts/openapi.json`, exported from the actual application. Regenerate frontend types with `npm run generate:api`. Older schemas in `deliverables/apexvibe5-handoff-v1/` remain design history.

## API sequence

1. GET `/v1/capabilities` and `/v1/entities`.
2. POST `/v1/cases` with independent buyer/seller selections: skip, existing, or manual.
3. POST `/v1/cases/{id}/invoice` with multipart file, expected_case_revision, replace=false. The 202 response means queued, not parsed.
4. Poll Workspace; display the real PDF and parsed data. PATCH parties to resolve conflicts explicitly.
5. POST assessments with expected_case_revision. Follow actual module states.
6. Automatically show the result only when initial_assessment_status=settled and navigation.target=result. Failure and needs_info also settle the initial batch.
7. Read aggregate.current_result and aggregate.decision without recalculating scores or financing in the browser.

## Module resources

Prefix: `/v1/cases/{id}/modules/{module_key}`.

| Action | Endpoint and fields |
|---|---|
| Read module | GET prefix |
| Upload evidence | POST /evidence, multipart files, expected_module_version, rerun |
| Versioned field sheet | Add evidence_group=invoice_field_sheet and explicit supersedes_evidence_id when replacing |
| Supplementary information | POST /supplements, JSON text, expected_module_version, rerun |
| Rerun | POST /runs, expected_module_version and reason |
| Manual adjustment | POST /adjustments, expected_module_version, applies_to_run_id, requested_adjustment, reason |
| Immutable run | GET /runs/{run_id} |
| Download | GET /v1/cases/{id}/files/{file_id} |
| State events | GET /v1/cases/{id}/events?after_seq=0&limit=100 |

Every write has an Idempotency-Key (8–128 characters). Retry the same logical request with the same key and body. A new action receives a new key. On 409, refresh and preserve drafts rather than silently replaying with a new version.

Combined file/text submission is two transactions: files with rerun=false, fetch the latest version, then the note with rerun=true. If the second operation fails, report accepted files and preserve the remaining note. A new field sheet is activated only after parsing succeeds; historical versions remain available.

## Display rules

Current risk is LOW or HIGH only. Null/currently unavailable scores display Pending, never zero. Historical last_valid_result is labeled explicitly. Pending/stale/failed modules cannot authorize current financing. A manual adjustment remains separate from the AI score and requires reconfirmation after a new AI run.

Corrected evidence is reassessed from its contents. Case 2 errors add 15 integrity points; the corrected active sheet removes them, so total risk drops **50 → 35**. The other six modules retain their runs. HIGH remains because the final score still exceeds the threshold.

Amounts are decimal strings, e.g. `"6400.00"`. The frontend formats them without floating-point financing calculations. The main PDF is read-only; replacement is supported, arbitrary field PATCH is not.

## Local configuration

Frontend origin: `http://127.0.0.1:3000`; API: `http://127.0.0.1:18080`. Allow the exact frontend CORS origin. Keep TeamRouter keys in the backend `.env`. User-facing labels, errors, AI summaries, findings, and missing-input descriptions are English; user-authored evidence is preserved verbatim.

The English demo database is isolated under `runtime/english-demo/` on this machine. Earlier test records are retained under the original runtime directory. This is local PC Web acceptance, not production deployment. No GitHub upload has occurred.
