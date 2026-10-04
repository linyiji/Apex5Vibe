# Case 2 relationship evidence demonstration

Verified locally on 4 October 2026 (Asia/Hong_Kong) with TeamRouter `gpt-6.1-sol`. This is a synthetic product demonstration. The uploaded ledger supplies newly authored fictional transactions; it is not a reconstruction of facts in the original four documents.

## Why the original four files leave 30 points

The main invoice supplies GBP 50,000. The local reference contains 12 comparable completed trades with a median of GBP 8,000. The ratio is 6.25. The current `TRADE_SCALE_HIGH` rule assigns 30 points when the ratio is at least 5.

| File | What it establishes in this demo |
|---|---|
| `ApexDefend_Case_2_Invoice.pdf` | Main invoice: 6,250 pieces at GBP 8, for GBP 50,000 |
| `ApexDefend_Case_2_Errors.xlsx` | Deliberate field errors: GBP 80,000 total and the seller's address copied into the buyer address |
| `ApexDefend_Case_2_Corrected.xlsx` | Corrected GBP 50,000 total and the buyer's UK address |
| `ApexDefend_Case_2_Additional_Evidence.pdf` | Supplier correction statement, purchase order, and buyer address confirmation supporting the same field corrections |

The corrected amount matches the amount Relationship already used. None of these four files supplies new historical transactions or changes the GBP 8,000 median. They can resolve an Invoice Integrity conflict, while the separate trade-scale finding remains. The current policy has no separate score reduction for a corroborating purchase order or an explanation of a larger order.

## What the additional workbook changes

Fixture: [`Apex5Vibe_Case_2_Relationship_Evidence.xlsx`](../deliverables/apexvibe5-handoff-v1/source/Apex5Vibe_Case_2_Relationship_Evidence.xlsx).

- `Relationship Evidence` records the invoice, comparison scope, dated summary, and synthetic provenance.
- `Comparable Trades` preserves all 12 original rows without changing their values and adds 16 distinct fictional records dated 1 August through 30 September 2026.
- The additional amounts range from GBP 32,000 to GBP 62,000. All rows use the same seller, buyer, SKU, and GBP currency, with a completed status and dates before the current invoice.
- After deduplication, there are 28 records. The two middle amounts are GBP 34,000 and GBP 36,000, giving a median of GBP 35,000. The current invoice ratio becomes `50,000 / 35,000 = 1.428571`.

The amount GBP 35,000 is a dataset median, not an approval threshold. Existing rules assign 0 points for a ratio below 2, 15 for a ratio from 2 up to 5, and 30 for a ratio of at least 5. No scoring code, threshold, manual adjustment, invoice amount, or database reference record was changed in this exercise.

The workbook is a dated literal-value snapshot because the evidence parser rejects formulas. Its records, unique IDs, dates, median, and source preservation were independently checked. Every added transaction is labeled synthetic. The sample was constructed to exercise the lower-risk branch of the demo.

## Reproduce locally

1. Start the frontend, API, and worker using the root README.
2. Create Case 2 with `ApexDefend_Case_2_Invoice.pdf`, resolve the parties, and run the initial assessment. The baseline is 35 HIGH: Relationship 30 plus Payment History 5.
3. In Buyer–Seller Relationship, choose Add note or document and select the additional relationship workbook. Click Send & reassess.
4. Wait for parsing and the independent AI run. Open Full view and inspect the selected rule and source citation.
5. In the verified run, AI selected `TRADE_SCALE_NORMAL`, cited the uploaded workbook, and assigned 0. The total became 5 LOW. The other six module run IDs and scores remained unchanged.

To demonstrate the original scenario again, create a fresh Case 2 without the additional relationship workbook. Existing run history remains available in Full view. The source files are reusable; local case and run IDs in validation records will differ in a new workspace.

## Verified result and limitations

The [validation record](validation/relationship-evidence-live.json) includes fixture hashes, the actual model identifiers, case/run IDs, before-and-after scores, and unchanged module checks. The downloaded evidence bytes were checked against the delivered workbook, and the browser showed 5 LOW after completion.

This proves that the local workflow can incorporate supplied historical rows and re-evaluate a module. It does not prove the additional trades occurred or that a real invoice became safer. The current system does not independently authenticate an uploaded ledger, its issuer, or its transaction amounts. The UI's indicative eligibility is a demo-policy result, not a real lending decision. Production use would require validated provenance, transaction corroboration, robust comparability and deduplication checks, and a reviewed financing policy.
