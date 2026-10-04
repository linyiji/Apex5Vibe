// STAND-IN for the AI that will read analyst notes and documents (mock mode only).
// The real version is an LLM in the backend that interprets the note and document
// contents. Here, documents count by file name and notes by simple keyword rules.

import type { EvidenceItem, ModuleId } from "./types";

const MODULE_NAMES: Record<ModuleId, string> = {
  invoice_integrity: "Invoice Integrity",
  buyer_verification: "Buyer Verification",
  seller_verification: "Seller Verification",
  transaction_plausibility: "Transaction Plausibility",
  relationship: "Buyer–Seller Relationship",
  payment_behaviour: "Payment Behaviour",
  duplicate_financing: "Duplicate Financing",
};

const NEGATIVE = /\b(not|never|didn'?t|did not|no|haven'?t|hasn'?t|unaware)\b/i;
const BANK_CONFIRMED = /\b(confirm\w*|email\w*|phone\w*|call\w*|rang|letter|notified|verified|told us|informed)\b/i;
const NO_PO = /\b(no|don'?t have|without|missing|can'?t find)\b.*\b(po|purchase order|contract)\b/i;

const quote = (t: string) => `“${t.length > 80 ? t.slice(0, 77) + "…" : t}”`;

export function interpretSubmission(moduleId: ModuleId, note: string, fileNames: string[]): EvidenceItem[] {
  const now = new Date().toISOString();
  const item = (field: string, value: boolean | string, label: string, detail: string, source: EvidenceItem["source"], confidence: EvidenceItem["confidence"]): EvidenceItem =>
    ({ field, value, label, detail, source, confidence, addedAt: now });
  const out: EvidenceItem[] = [];
  const text = note.trim();

  // Every note is kept on the record against its module.
  if (text) out.push(item("analyst_note", moduleId, "Analyst note", quote(text), "analyst_note", "user_provided"));

  // Documents: a bank letter or PO resolves the matching check; others are attached only.
  for (const name of fileNames) {
    if (moduleId === "seller_verification")
      out.push(item("bank_account_change_confirmed", true, "Bank account ownership document", name, "upload", "document"));
    else if (moduleId === "transaction_plausibility")
      out.push(item("po_provided", true, "Purchase order supplied", name, "upload", "document"));
    else out.push(item("supporting_document", moduleId, `Supporting document · ${MODULE_NAMES[moduleId]}`, name, "upload", "document"));
  }

  // Notes without a document: simple keyword reading of the analyst's statement.
  if (text && !fileNames.length) {
    if (moduleId === "seller_verification" && BANK_CONFIRMED.test(text))
      out.push(NEGATIVE.test(text)
        ? item("bank_account_change_confirmed", false, "Bank change not notified", quote(text), "analyst_note", "user_provided")
        : item("bank_account_change_confirmed", true, "Bank account change confirmed", quote(text), "analyst_note", "user_provided"));
    if (moduleId === "transaction_plausibility" && NO_PO.test(text))
      out.push(item("po_provided", false, "No purchase order available", quote(text), "analyst_note", "user_provided"));
  }
  return out;
}
