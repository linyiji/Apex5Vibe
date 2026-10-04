# Apex5Vibe — Modular Assessment Workspace

A local **English-language PC Web demo** with a Next.js frontend, FastAPI backend, SQLite database, and independent workers. The backend calls TeamRouter using **gpt-6.1-sol** to assess seven invoice risk modules against selected local evidence.

**Higher scores mean higher invoice risk. LOW < 30; HIGH ≥ 30.** Corrected evidence can remove a finding and lower the module and aggregate scores. A risk reduction does not automatically imply LOW: the Case 2 field-correction flow demonstrates **35 → 50 → 35 HIGH**. An optional, separately authored synthetic trade-ledger fixture demonstrates **35 HIGH → 5 LOW** by changing the comparable-history dataset.

The frontend uses the real `/v1` API by default. It uploads file bytes and displays persisted AI results; it does not calculate scores locally or fall back to a mock result on failure. Scope is desktop PC browsers. Mobile adaptation and production deployment are outside this demo.

## Start locally

Python 3.12 and Node 24 are used in this workspace. From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
cp -n .env.example .env
```

Set `TEAMROUTER_API_KEY` in the root `.env`. The configured endpoint is `https://api.teamorouter.com/v1` and the model is `gpt-6.1-sol`. Keep this key on the backend. Initialize the database and start the API:

```bash
python -m apexdefend.manage init
uvicorn apexdefend.api:create_app --factory --host 127.0.0.1 --port 18080
```

Start a worker in another terminal with the same virtual environment and working directory:

```bash
python -m apexdefend.worker
```

One worker is sufficient; two workers were used during browser acceptance to process independent modules concurrently. Both must share the API's `.env` and `APEX_DATA_DIR`.

Start the frontend in a third terminal:

```bash
cd frontend
npm ci
cp -n .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Existing frontend settings must be `NEXT_PUBLIC_API_MODE=live` and `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:18080` (no `/v1` suffix).

- Application: <http://127.0.0.1:3000>
- API reference: <http://127.0.0.1:18080/docs>
- Configuration/health: <http://127.0.0.1:18080/health>
- Default storage: `runtime/apex.sqlite3` and `runtime/files/`, configurable with `APEX_DATA_DIR`.
- This machine's English demo uses `runtime/english-demo/`. Earlier acceptance data remains in `runtime/` and has not been deleted. Both are ignored by Git.

## Demonstrate the two cases

Use the source files in `deliverables/apexvibe5-handoff-v1/source/`. They are synthetic demo documents.

| Flow | Expected result |
|---|---|
| Case 1 PDF → Run Assessment | 5 / LOW, eligible, GBP 6,400.00 indicative advance |
| Case 2 PDF → Run Assessment | 35 / HIGH, manual review, no automatic advance |
| Case 2 Invoice Integrity → Errors.xlsx → Send & reassess | 50 / HIGH; integrity increases from 0 to 15 |
| Same module → Corrected.xlsx → Replace current field sheet → Send & reassess | 35 / HIGH; integrity decreases from 15 to 0 |
| Case 2 Relationship → Apex5Vibe_Case_2_Relationship_Evidence.xlsx → Send & reassess | 5 / LOW; relationship decreases from 30 to 0 using additional synthetic history |

The corrected sheet supersedes the erroneous sheet only after successful parsing and validation. The old evidence and AI run stay in history. The main PDF and the other six modules remain unchanged.

The optional relationship workbook preserves 12 local reference trades and adds 16 fictional demonstration trades. The combined median becomes GBP 35,000 and the current invoice/median ratio becomes 1.43. These additional trades are **not facts extracted from the original invoice, error sheet, correction sheet, or supporting PDF**. The original four files alone leave the relationship baseline at GBP 8,000 and the relationship score at 30. See [Relationship evidence demo](docs/relationship-evidence-demo.md) for the distinction, reproducible steps, and verification.

Buyer and Seller independently support Skip, Select existing, and Manual. Review displays the original PDF and read-only extracted fields. Resolve any company conflict before starting. Step 3 automatically opens the result after the initial batch settles, including failed or incomplete assessments.

Modules support supplementary text, PDF/XLSX/CSV evidence, Save only, Send & reassess, independent AI reruns, manual adjustments, and Full view. Pending or stale assessments show the previous score as historical and withhold a current financing amount. Manual adjustments are separate from AI scores and require confirmation after a new AI run.

## Verification and contracts

```bash
ruff check backend scripts
ruff format --check backend scripts
pytest
python scripts/export_openapi.py --check
cd frontend
npm run generate:api
npm run lint
npm run typecheck
npm run build
```

The runtime contract is [`contracts/openapi.json`](contracts/openapi.json). The frontend generates its DTOs from that file. Older contracts in the architecture archive are design history.

Optional real-model API acceptance scripts (each creates a new case and calls TeamRouter):

```bash
python scripts/live_case1.py --verify-rerun
python scripts/live_case2.py
```

Offline tests use an explicitly marked test analyzer. They are separate from real AI and browser acceptance.

- [PC Web integration and frontend startup](frontend/README.md)
- [Live browser acceptance](frontend/docs/05-live-integration-verification.md)
- [Backend implementation](docs/backend-implementation.md)
- [API integration](docs/frontend-integration.md)
- [Demo runbook](docs/demo-runbook.md)
- [Relationship evidence demo and limitations](docs/relationship-evidence-demo.md)
- [Earlier backend acceptance](docs/validation/README.md)
- [Original architecture archive](deliverables/apexvibe5-handoff-v1/README.md)

The service is a local demonstration with a fixed analyst identity and synthetic reference data. It supports the supplied invoice AcroForm template and text-based evidence, not general scanned-invoice OCR. Images, Word, and legacy XLS are unavailable. Authentication, multi-tenancy, external registries, independent verification of uploaded trade records, and actual financing execution are outside scope. The GitHub repository contains the source, synthetic fixtures, and validation records; the application still runs locally.
