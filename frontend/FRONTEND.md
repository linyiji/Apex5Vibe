> 本地整理说明（2026-10-04）：以下保留原作者的四接口原型设计。工作区后端使用不同的 /v1 契约，不能只切换模式完成联调；请先看 [后端联调准备](docs/03-backend-integration.md)。

# ApexVibe Frontend — Handover Guide

**ApexVibe** is an invoice financing risk assessment tool for lenders, factoring companies and
trade-finance platforms. The whole interface answers one question:

> **"Should we finance this invoice, and why?"**

This folder is the **frontend only**. It runs end to end on its own using a built-in mock
backend, so it can be demoed without any server. When the Python backend is ready, one setting
switches it over.

---

## 1. Quick start

Requirements: **Node.js 20+** (tested on Node 24) and npm.

```bash
npm install          # first time only (restores node_modules, not included in the zip)
npm run dev          # http://localhost:3000
```

Other commands:

| Command | Does |
|---|---|
| `npm run build` | Production build (also type-checks) |
| `npm start` | Serve the production build |
| `npm run lint` | ESLint |

### Configuration (optional)

Copy `.env.example` to `.env.local`:

```
NEXT_PUBLIC_API_MODE=mock                    # mock (default) | live
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- **mock**: the scoring engine and the AI reading of notes/documents are simulated in the
  browser. The header shows a **"Demo · simulated engine"** badge and the footer says so.
- **live**: all calls go to the FastAPI backend at `NEXT_PUBLIC_API_BASE_URL`. The backend
  must allow CORS from `http://localhost:3000`.

---

## 2. Tech stack

- **Next.js 16** (App Router) + **React 19** + **TypeScript**
- **Tailwind CSS 4** (theme colours defined in `app/globals.css`)
- **lucide-react** icons
- No other runtime dependencies

> Note: Next.js 16 has breaking changes from older versions. `AGENTS.md` points to the docs
> bundled in `node_modules/next/dist/docs/`, so check those before changing routing APIs.

---

## 3. User flow

```
Upload ──► Review ──► Assessment ──► Decision ──► (notes / documents) ──► Reassess ──► Decision v2 …
```

1. **Upload** (`/`): drop a PDF/PNG/JPG or click **Use Demo Invoice**. Past evaluations from this
   browser session are listed underneath.
2. **Review** (`/assessment/[id]`): invoice preview on the left, extracted fields on the right.
   Each field is marked **extracted**, **uncertain**, **missing** or **edited**. Fix anything, then
   **Run Assessment**.
3. **Assessment**: short processing state while the seven risk modules run.
4. **Decision**: same page, showing:
   - **Finance / Risk score / Advance / Information completeness** at the top
   - **Preliminary** warning while important information is missing
   - **Why might this be high risk?** (medium/high only): plain-English drivers with
     *What to check* and an **Add note or document** button
   - **Why this score**: the seven modules, each expandable to its checks and evidence
   - **Assessment completeness** (right): verified vs missing items, each missing item has **Add evidence**
   - **Analyst notes & documents** (right): pick a risk area, write a note, attach files,
     **Send & reassess**
5. **Reassess**: processing overlay, then the page updates in place with a **score change**
   panel (old → new score, band change, per-module *Before / After*). Repeat as often as needed.

---

## 4. Demo script (mock mode)

1. **Use Demo Invoice** → review: *PO reference* is **uncertain**, *Buyer registration* is **missing** → **Run Assessment**
2. Result: **23 / 100 · Medium risk · Manual review · 71% complete · Preliminary**
3. Under **Bank details changed**, click **Add note or document** (opens Seller Verification).
   Type *"Supplier emailed us on 2 Oct confirming the new account"* → **Send & reassess**
4. **23 → 9 · Medium → Low · −14 points**: *Eligible*, 80% advance (£3,224). "What changed?"
   shows Seller Verification before and after.
5. In completeness, **Add evidence** next to *Purchase order* → attach any file → **Send & reassess**
   → **9 → 5**, 100% complete, no longer preliminary.

Other paths to show:

| Risk area | Input | Result |
|---|---|---|
| Seller Verification | note: *"They never notified us of any change"* | 23 → **33 High**, do not finance |
| Seller Verification | any file (treated as a bank letter) | 23 → **7 Low** |
| Transaction Plausibility | note: *"We don't have a PO for this"* | 23 → **27 High** |
| Any other area | any note or file | recorded in that module's evidence; score unchanged (the UI says so) |

---

## 5. Scoring rules used by the mock

All numbers are **demo placeholders**, not a validated credit policy.

```
score = min(100, sum of module points)
band  = low     0–10   → Eligible, 80% advance
        medium  11–25  → Manual review, financing pending
        high    > 25   → Do not finance
completeness = verified items / 7 required items  (< 100% ⇒ "Preliminary")
```

| Module | Points in the demo |
|---|---|
| Invoice Integrity | 0 |
| Buyer Verification | 0 |
| Seller Verification (bank account) | unverified **16** · confirmed by note **2** · document **0** · not notified **26** |
| Transaction Plausibility (PO) | unverified **4** · PO supplied **0** · no PO **8** |
| Buyer–Seller Relationship | 0 |
| Payment Behaviour | **3** (2 of 12 invoices paid late) |
| Duplicate Financing | 0 |

**Unknown is never treated as safe:** an unverified item adds points *and* lowers completeness.

Constants live in `lib/mock-data.ts` (`POINTS`, `BAND_LIMITS`, `ADVANCE_RATE_LOW`).

---

## 6. Folder structure

```
app/
  layout.tsx                 header, footer, fonts, mock-mode notice
  page.tsx                   Upload screen + Past evaluations
  globals.css                Tailwind theme (navy / cyan palette)
  assessment/[id]/page.tsx   Review → processing → decision for one case

components/
  Header.tsx                 Logo, "Demo · simulated engine" badge, New assessment
  StepIndicator.tsx          Subtle Upload → Review → Assessment → Decision progress
  InvoiceUploader.tsx        Drag-and-drop + Upload Invoice + Use Demo Invoice
  PastEvaluations.tsx        Assessments run in this browser session
  InvoicePreview.tsx         Uploaded file (PDF/image) or rendered demo invoice
  InvoiceFieldsForm.tsx      Editable fields with extracted/uncertain/missing/edited status
  ProcessingState.tsx        Animated step list (initial assessment + reassessment)
  DecisionView.tsx           Decision page layout + submit → reassess orchestration
  AssessmentSummary.tsx      Finance / Risk score / Advance / Completeness strip
  RiskScore.tsx              Big score that counts old → new after a reassessment
  ScoreChange.tsx            "23 → 9", band change, What changed? before/after
  RiskDrivers.tsx            "Why might this be high risk?" + What to check
  RiskFactorCard.tsx         One module row (expandable)
  EvidencePanel.tsx          A module's checks and evidence
  MissingInformation.tsx     Assessment completeness panel
  AnalystInput.tsx           Notes + attachments → Send & reassess

lib/
  types.ts                   DATA CONTRACTS shared with the backend
  api.ts                     The ONLY file that calls the backend (mock or live)
  case-store.ts              Per-tab UI state in sessionStorage (cases, past evaluations)
  format.ts                  Money/date formatting, band/recommendation labels & colours
  mock-data.ts               Demo invoice, synthetic reference data, scoring constants
  mock-engine.ts             Mock stand-in for the backend scoring engine
  mock-notes.ts              Mock stand-in for the AI that reads notes and documents
```

---

## 7. Backend API contract

Everything goes through `lib/api.ts`. In **live** mode it calls:

| Function | Method & path | Request | Response |
|---|---|---|---|
| `extractInvoice(file)` | `POST /api/invoices/extract` | multipart `file` | `ExtractedInvoice` |
| `runAssessment(invoice)` | `POST /api/assessments` | JSON `{ invoice }` | `Assessment` |
| `getAssessment(id)` | `GET /api/assessments/{id}` | — | `Assessment` |
| `submitAnalystInput(...)` | `POST /api/assessments/{id}/reassess` | multipart `module_id`, `note`, `files` (repeated) | new `Assessment` with `previous` filled |

Errors: return a non-2xx status with `{ "detail": "readable message" }`. The UI shows `detail` as-is.

### Key types (full definitions in `lib/types.ts`)

```ts
ExtractedInvoice {
  file_name: string
  simulated: boolean              // true = demo values, not read from the file
  fields: Record<InvoiceFieldKey, { value: string | null, status: "extracted"|"uncertain"|"missing"|"edited", source: string | null }>
  line_items: { description, quantity, unit_price, amount }[]
}
// InvoiceFieldKey: seller, buyer, buyer_registration, invoice_number, invoice_date,
//                  due_date, amount, currency, bank_account, po_reference

Assessment {
  id, version, createdAt
  invoice: ExtractedInvoice
  score: number                   // 0–100
  band: "low" | "medium" | "high"
  recommendation: "eligible" | "manual_review" | "decline"
  advanceRate: number | null      // 0.8 = 80%; null when not offered
  financingAmount: number | null
  modules: RiskModule[]           // all 7, always
  drivers: RiskDriver[]           // plain-English reasons + whatToCheck[]
  completeness: { percent, items: { id, label, status: "verified"|"missing", note, moduleId }[] }
  evidence: EvidenceItem[]        // everything submitted so far
  preliminary: boolean            // true while important info is missing
  previous: AssessmentSnapshot | null   // last version, for the score-change panel
}

RiskModule { id, name, description, status: "clear"|"watch"|"risk", points, summary,
             checks: { label, result: "pass"|"warn"|"fail"|"unknown", detail }[],
             evidence: { label, value, source }[] }

EvidenceItem { field, value, label, detail,
               source: "analyst_note" | "upload" | "reference_data",
               confidence: "user_provided" | "document" | "verified", addedAt }
```

Module ids: `invoice_integrity`, `buyer_verification`, `seller_verification`,
`transaction_plausibility`, `relationship`, `payment_behaviour`, `duplicate_financing`.

**Rule for the backend:** the AI may extract fields and turn notes/documents into evidence,
but the **score and recommendation must come from fixed rules**, never from the AI.

---

## 8. What is real vs simulated

| Part | Status |
|---|---|
| UI flow, field editing, score-change view, past evaluations | **Real** (works in the browser) |
| File upload and preview | **Real**: the file is shown; in mock mode it isn't sent anywhere |
| Invoice extraction | **Simulated**: mock returns the demo invoice values, labelled "Simulated extraction" |
| Risk scoring | **Simulated**: `lib/mock-engine.ts` reproduces the demo numbers |
| Reading analyst notes | **Simulated**: simple keyword rules in `lib/mock-notes.ts` |
| Reading attached documents | **Simulated**: only the file name is used; contents are not read |
| Reference data (registries, payment history, bank on file) | **Synthetic**: fictional companies |

The UI labels all of the above, so judges can see what is real.

---

## 9. State and persistence

- Cases and past evaluations live in the browser's **sessionStorage**. They survive a refresh
  but disappear when the tab is closed.
- Uploaded file previews only live in memory, so after a refresh the review screen shows the
  rendered demo layout instead of the original file.
- In mock mode the "backend" assessments are also kept in sessionStorage.

---

## 10. Design notes

- Dark navy background, one cyan accent. **Green** = verified, **amber** = uncertain,
  **red** = significant risk only.
- The decision page should be understandable in about 5 seconds: verdict and numbers first,
  reasons next, details on expand.
- Actions are small boxed buttons (e.g. **Add note or document**, **Add evidence**), not text links.
- Design references: `ApexVibe5_modular_assessment_v2.html` and
  `ApexVibe5_Invoice_Assessment_Design_Report_EN.pdf` (seven modules, local reprocessing loop,
  separate manual input).

---

## 11. Next steps

1. Backend: implement the four endpoints in §7 with the same JSON shapes.
2. Set `NEXT_PUBLIC_API_MODE=live` and test the demo script against the backend.
3. Replace `mock-notes.ts` behaviour with real AI reading of notes and documents (backend side).
4. Optional: persistent case history (needs a backend store).
