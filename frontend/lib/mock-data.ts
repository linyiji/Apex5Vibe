// Demo invoice and synthetic reference data used by the mock API.
// Based on the Apex5Vibe design report demo case (INV-2026-014), extended with
// a changed bank account and an unverified PO so the AI Risk Analyst has
// something to resolve. All values are fictional.

import type { ExtractedInvoice, InvoiceField, InvoiceFieldKey } from "./types";

const f = (value: string | null, status: InvoiceField["status"], source: string | null): InvoiceField => ({
  value,
  status,
  source,
});

export const DEMO_FILE_NAME = "INV-2026-014_Adaeze_Okonkwo_Studio.pdf";

export function demoInvoice(fileName = DEMO_FILE_NAME, simulated = false): ExtractedInvoice {
  const fields: Record<InvoiceFieldKey, InvoiceField> = {
    seller: f("Adaeze Okonkwo Studio", "extracted", "Adaeze Okonkwo Studio, 18 Shoreditch High Street, London"),
    buyer: f("Harbour & Vine Ltd", "extracted", "Bill to: Harbour & Vine Ltd, 22 Rivington Street"),
    buyer_registration: f(null, "missing", null),
    invoice_number: f("INV-2026-014", "extracted", "Invoice No. INV-2026-014"),
    invoice_date: f("2026-09-14", "extracted", "Issue date: 14 Sep 2026"),
    due_date: f("2026-10-14", "extracted", "Due: 14 Oct 2026"),
    amount: f("4030.00", "extracted", "TOTAL £4,030.00"),
    currency: f("GBP", "extracted", "All amounts in GBP"),
    bank_account: f("20-45-77 ••••4821", "extracted", "Sort code 20-45-77  Account 6119 4821"),
    po_reference: f("PO-20931", "uncertain", "Your ref: P0-20931 (smudged: 0 or O?)"),
  };
  return {
    file_name: fileName,
    simulated,
    fields,
    line_items: [
      { description: "Brand Identity Package", quantity: 1, unit_price: 2400, amount: 2400 },
      { description: "Website Design", quantity: 3, unit_price: 450, amount: 1350 },
      { description: "Post-launch Support (hours)", quantity: 6, unit_price: 80, amount: 480 },
    ],
  };
}

export const DEMO_TOTALS = { subtotal: 4230, discount: 200, tax: 0 };

/** Reference records the mock engine "looks up". Synthetic. */
export const REFERENCE = {
  sellerAccountOnFile: "20-45-77 ••••0937",
  sellerAccountVerified: "3 Nov 2025",
  sellerSince: "Mar 2024",
  priorInvoicesBetweenParties: 6,
  typicalInvoiceValue: "£3,200–£4,800",
  marketBenchmark: "£350–£600 per website-design day",
  paymentHistory: { invoices: 12, onTime: 10, late: 2, avgDaysLate: 6, defaults: 0 },
};

/** Points per module under each evidence state (placeholders, see FRONTEND.md §5). */
export const POINTS = {
  bankUnverified: 16,
  bankConfirmed: 2,
  bankDocumented: 0,
  bankNotNotified: 26,
  poUnverified: 4,
  poProvided: 0,
  poUnavailable: 8,
  paymentLate: 3,
};

export const ADVANCE_RATE_LOW = 0.8;

/** Band thresholds: low ≤ 10, medium 11–25, high > 25. */
export const BAND_LIMITS = { lowMax: 10, mediumMax: 25 };
