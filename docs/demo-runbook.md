# English PC Web Demo Runbook

## Start

Follow the root README to start API port 18080, at least one worker, and Next.js port 3000. The API and workers must use the same APEX_DATA_DIR. `/health` confirms configured model and key presence; only a real assessment proves provider connectivity.

Open <http://127.0.0.1:3000>. Confirm the **Live AI assessment** badge. The current local `.env` selects `runtime/english-demo/`; earlier tests remain untouched in `runtime/`.

## Case 1: low risk

1. Select Skip for Buyer and Seller. Upload `ApexDefend_Case_1_Invoice.pdf`.
2. Review GBP 8,000.00, invoice CV-2026-1002-001, and matched companies. Refresh once if demonstrating server persistence; the original PDF remains available.
3. Click Run Assessment. Modules run independently, then Step 4 opens automatically.
4. Expected result: **5 / LOW**, eligible, **GBP 6,400.00** indicative advance. Payment History contributes 5; the other modules contribute 0.
5. Payment History → Add note or document. Enter: `Local records show 2 late payments out of 12 completed payments. No new independent payment evidence is available.`
6. Save only: the target module becomes stale, current financing becomes Pending, and the previous result remains clearly historical. Re-run AI: only this module is re-evaluated. Unchanged facts may leave the score at 5.
7. Full view exposes English findings, citations, evidence, notes, adjustments, and immutable AI run inputs.

Optional adjustment demonstration: apply -5 with a reason, observe the original AI 5 alongside manual -5 and final 0. Rerun the module: the old adjustment requires confirmation and financing is Pending. Apply 0 to the new run to restore the unadjusted score of 5.

## Case 2: high risk, then correction lowers risk

1. Upload `ApexDefend_Case_2_Invoice.pdf`, review GBP 50,000.00, and start assessment.
2. Initial result: **35 / HIGH**, manual review, no automatic advance. Relationship contributes 30 and Payment History contributes 5.
3. Invoice Integrity → Add note or document → choose `ApexDefend_Case_2_Errors.xlsx` → Send & reassess. Result: **50 / HIGH**. Integrity is 15 because the sheet conflicts with the main PDF's buyer address and total.
4. Choose `ApexDefend_Case_2_Corrected.xlsx`. Check **Replace current field sheet**, then Send & reassess.
5. Result: **35 / HIGH**, with **Risk decreased by 15 points: 50 → 35**. Integrity drops to 0. This is a content-based correction; the other six module runs and the main PDF remain unchanged.
6. Full view shows Errors as superseded and Corrected as active, plus the original 0 → 15 → 0 AI run history. The erroneous version remains auditable and downloadable.

A valid correction reduces the risk finding it resolves. It does not erase unrelated relationship/payment risk or automatically turn HIGH into LOW.

## Optional Case 2 relationship demonstration

Use `Apex5Vibe_Case_2_Relationship_Evidence.xlsx` from the source fixture directory in Buyer–Seller Relationship, then click Send & reassess. In the verified run, that module decreased from 30 to 0 and the total decreased from 35 HIGH to 5 LOW. No manual adjustment was applied; the other six module runs stayed unchanged.

This workbook adds 16 **fictional demonstration trades** to the 12 existing local reference records. It changes the combined median from GBP 8,000 to GBP 35,000. It is a different evidence scenario from correcting the invoice's fields. The original invoice, Errors, Corrected, and Additional Evidence files do not contain these added historical transactions and do not alone remove the 30-point trade-scale finding. See [Relationship evidence demo](relationship-evidence-demo.md) for the exact calculation, provenance, and current verification limitations.

## Troubleshooting

| Symptom | Action |
|---|---|
| Jobs stay queued | Start a worker with the same data directory as the API |
| TeamRouter not configured | Populate the root backend .env and restart API/workers |
| Provider timeout / 408 / 429 / 5xx | The worker allows at most three attempts; a terminal failure remains visible and can be rerun |
| Invalid AI output/citation/rule | Inspect Full view and the run error; correct the input/prompt and rerun the target module, never insert zero |
| Needs information | Check missing_inputs; supply genuine missing data or correct input interpretation |
| Stale / Pending | Wait for parsing and rerun the affected module; previous financing is not current |
| Adjustment needs confirmation | Review the new AI run and apply a new adjustment, including 0 if no adjustment is warranted |
| Version conflict | Refresh and review the current module; the UI preserves the unsent draft |
| Unsupported main PDF | Use the supplied commercial invoice form; general OCR is not configured |
| Spreadsheet formulas | Convert formulas to values before uploading |
| Evidence replacement blocked | Explicitly select the current active version in the same case/module/group |

The queue offers Low/High filters and persistent case links. Both cases can be reopened after refresh or process restart. Keep `.env`, runtime databases, uploaded files, and dependency directories out of GitHub. The supplied invoices and reference records are synthetic, and the app performs no actual financing transaction.
