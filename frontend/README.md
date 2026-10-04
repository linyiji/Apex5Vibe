# Apex5Vibe PC Web Frontend

The Next.js frontend connects to the local FastAPI **`/v1`** API. **Live is the default.** Invoices, evidence, supplementary information, AI runs, and adjustments are stored on the backend. TeamRouter uses **gpt-6.1-sol**; the browser never receives the API key.

The product, AI-generated assessment text, and API errors use **English**. Source documents and user-authored evidence retain their original contents. Scope is PC desktop browsers only.

## Run locally

Start the API and worker using the [root README](../README.md), then:

```bash
cd /Users/mac/Apex5vibe/frontend
npm ci
cp -n .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open <http://127.0.0.1:3000>. Node 24 is specified in `.nvmrc`.

For an existing installation, update `.env.local`:

```dotenv
NEXT_PUBLIC_API_MODE=live
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:18080
```

The URL is an origin without a `/v1` suffix. NEXT_PUBLIC values are public and fixed at production build time. TeamRouter credentials belong only in the root backend `.env`.

## Demo

1. Select Skip, Select existing, or Manual independently for Buyer and Seller; upload the supplied Case 1 or Case 2 PDF.
2. Review the original PDF, extracted fields, and company matching. Resolve a conflict with **Use invoice buyer/seller**. Fields are read-only; use a replacement PDF to correct the main invoice.
3. Click **Run Assessment**. Real module states are shown; the initial batch automatically opens the result when settled. Failures and missing information are displayed explicitly.
4. Case 1: **5 / LOW / GBP 6,400.00**. Case 2: **35 / HIGH / Manual review**.
5. Case 2 → Invoice Integrity → **Add note or document** → upload Errors.xlsx → **Send & reassess**: **50 / HIGH**.
6. Upload Corrected.xlsx, explicitly select **Replace current field sheet**, and submit: **35 / HIGH**. The page displays **Risk decreased by 15 points: 50 → 35**. Other modules retain their existing runs.
7. Explore **Full view**, evidence versions, AI run inputs, findings and citations, supplementary information, and adjustment history.

Each module also offers Save only, Re-run AI, and Manual adjustment. Higher means riskier; only LOW/HIGH are risk bands. Pending and stale results are separate states. A selected file alone does not change the score. A correction is evaluated against its content; attachments never automatically receive a discount.

## Checks

```bash
npm run generate:api
npm run lint
npm run typecheck
npm run build
# Stop the development server on port 3000 before running a production preview:
npm start -- --hostname 127.0.0.1 --port 3000
```

API types are generated with pinned openapi-typescript 7.13.0 from [the runtime OpenAPI](../contracts/openapi.json). The build uses next/font/google and needs access to the font service.

## Implementation map

| File | Responsibility |
|---|---|
| `lib/runtime-config.ts` | Live default; explicit mock opt-in |
| `lib/backend-api.ts` | HTTP, real multipart uploads, stable retry keys, revisions and errors |
| `lib/backend-types.ts`, `backend-schema.d.ts` | Generated DTOs, module labels, decimal-string formatting |
| `lib/use-workspace.ts` | Polling, cancellation, revision ordering, previous result |
| `components/live/UploadWorkspace.tsx` | Company selection, invoice upload, persisted queue |
| `components/live/AssessmentWorkspace.tsx` | Review, real progress, automatic result navigation |
| `components/live/ModuleCard.tsx` | Evidence, notes, adjustments, Full view and history |
| `components/live/InvoiceDocument.tsx` | Persistent file_id-based PDF preview |

[Integration details](docs/03-backend-integration.md) explain state and transaction boundaries. [Live acceptance](docs/05-live-integration-verification.md) records actual results and screenshots.

## Historical prototype

The original frontend archive and its preparation documents are retained for provenance: [source manifest](docs/source-manifest.json), [original overview](docs/01-codebase-overview.md), [old four-endpoint API](docs/02-current-api.md), and [Mock verification](docs/04-verification.md). They describe the pre-integration prototype, not current Live behavior.

`lib/api.ts` now serves only explicit Mock mode. Live never uses simulated scoring or a fallback on backend failure. The original ZIP in Downloads is unchanged. Dependencies, build outputs, local environment files, and databases are ignored by Git. No GitHub upload has been performed.
