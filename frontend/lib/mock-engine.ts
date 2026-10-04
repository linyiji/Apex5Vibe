// STAND-IN for the backend risk engine (mock mode only).
// The real scoring lives in the Python backend (CLAUDE.md §7). This file only
// reproduces the scripted demo numbers so the UI can be demonstrated offline.

import { ADVANCE_RATE_LOW, BAND_LIMITS, POINTS, REFERENCE } from "./mock-data";
import { money, parseAmount } from "./format";
import type {
  Assessment,
  AssessmentSnapshot,
  CompletenessItem,
  EvidenceItem,
  ExtractedInvoice,
  ModuleId,
  ModuleStatus,
  Recommendation,
  RiskBand,
  RiskDriver,
  RiskModule,
} from "./types";

const statusFor = (points: number): ModuleStatus => (points === 0 ? "clear" : points < 10 ? "watch" : "risk");

export function bandFor(score: number): RiskBand {
  if (score <= BAND_LIMITS.lowMax) return "low";
  if (score <= BAND_LIMITS.mediumMax) return "medium";
  return "high";
}

const RECOMMENDATION: Record<RiskBand, Recommendation> = {
  low: "eligible",
  medium: "manual_review",
  high: "decline",
};

function evidenceSource(e: EvidenceItem): string {
  return e.source === "upload" ? "Uploaded by analyst (contents not read in prototype)" : e.source === "analyst_note" ? "Analyst note" : "Reference data";
}

function latest(evidence: EvidenceItem[], field: string): EvidenceItem | undefined {
  return [...evidence].reverse().find((e) => e.field === field);
}

export function computeAssessment(
  invoice: ExtractedInvoice,
  evidence: EvidenceItem[],
  meta: { id: string; version: number; previous: AssessmentSnapshot | null },
): Assessment {
  const fx = invoice.fields;
  const amount = parseAmount(fx.amount.value);
  const currency = fx.currency.value;
  const bank = latest(evidence, "bank_account_change_confirmed");
  const po = latest(evidence, "po_provided");

  // ---- Seller verification: bank account consistency ----
  const bankDocumented = bank?.value === true && bank.confidence === "document";
  const bankPoints =
    bank === undefined ? POINTS.bankUnverified
    : bankDocumented ? POINTS.bankDocumented
    : bank.value === true ? POINTS.bankConfirmed
    : POINTS.bankNotNotified;
  const bankCheck =
    bank === undefined
      ? { result: "fail" as const, detail: `Invoice account ${fx.bank_account.value ?? "—"} differs from verified account ${REFERENCE.sellerAccountOnFile}. Change not yet confirmed.` }
      : bankDocumented
        ? { result: "pass" as const, detail: `Account ownership document supplied (${bank.detail}).` }
        : bank.value === true
          ? { result: "warn" as const, detail: `Change confirmed by analyst (${bank.detail}). Residual risk until account ownership is documented.` }
          : { result: "fail" as const, detail: "Analyst reports the seller never notified a bank change. Possible payment redirection." };

  // Supporting documents uploaded for modules whose score they don't (yet) change.
  // Notes and documents the analyst attached to each module, shown in its evidence list.
  const docsFor = (id: ModuleId) =>
    evidence
      .filter((e) => (e.field === "supporting_document" || e.field === "analyst_note") && e.value === id)
      .map((e) => ({ label: e.label, value: e.detail, source: evidenceSource(e) }));

  // ---- Transaction plausibility: purchase order ----
  const poPoints = po === undefined ? POINTS.poUnverified : po.value === true ? POINTS.poProvided : POINTS.poUnavailable;
  const poCheck =
    po === undefined
      ? { result: "unknown" as const, detail: `${fx.po_reference.value ?? "No PO"} not found in the buyer's purchase-order records.` }
      : po.value === true
        ? { result: "pass" as const, detail: `PO supplied by analyst (${po.detail}).` }
        : { result: "warn" as const, detail: "No purchase order or contract available for this transaction." };

  const p = REFERENCE.paymentHistory;
  const modules: RiskModule[] = [
    {
      id: "invoice_integrity",
      name: "Invoice Integrity",
      description: "Arithmetic, dates, numbering and document manipulation",
      status: "clear",
      points: 0,
      summary: "Totals, dates and numbering are consistent.",
      checks: [
        { label: "Invoice arithmetic", result: "pass", detail: "£4,230 − £200 discount + £0 tax = £4,030" },
        { label: "Date consistency", result: "pass", detail: "Due 30 days after issue; issue date not in the future" },
        { label: "Invoice number pattern", result: "pass", detail: "Follows the seller's sequence (INV-2026-013 → 014)" },
        { label: "Document manipulation", result: "pass", detail: "No editing-tool metadata detected" },
      ],
      evidence: [{ label: "Source invoice", value: invoice.file_name, source: "Uploaded document" }],
    },
    {
      id: "buyer_verification",
      name: "Buyer Verification",
      description: "Company existence, status and registered address",
      status: "clear",
      points: 0,
      summary: "Harbour & Vine Ltd is active and the address matches the registry.",
      checks: [
        { label: "Company exists", result: "pass", detail: "Found in company registry (synthetic record)" },
        { label: "Active status", result: "pass", detail: "Active, incorporated 2014" },
        { label: "Registered address", result: "pass", detail: "22 Rivington Street matches registry" },
      ],
      evidence: [{ label: "Company profile", value: "Harbour & Vine Ltd · ENT-002", source: "Reference data (synthetic)" }],
    },
    {
      id: "seller_verification",
      name: "Seller Verification",
      description: "Seller identity, business activity and bank account consistency",
      status: statusFor(bankPoints),
      points: bankPoints,
      summary:
        bank === undefined
          ? "Payment account differs from the seller's verified account."
          : bankDocumented
            ? "Bank change supported by an account ownership document."
            : bank.value === true
            ? "Bank change confirmed by analyst; ownership not yet documented."
            : "Unannounced bank change: strong redirection-fraud signal.",
      checks: [
        { label: "Company exists", result: "pass", detail: "Adaeze Okonkwo Studio, active (synthetic record)" },
        { label: "Business activity", result: "pass", detail: "Design studio; invoiced services match activity" },
        { label: "Bank account consistency", ...bankCheck },
      ],
      evidence: [
        { label: "Account on invoice", value: fx.bank_account.value ?? "—", source: "Uploaded document" },
        { label: "Verified account on file", value: `${REFERENCE.sellerAccountOnFile} (verified ${REFERENCE.sellerAccountVerified})`, source: "Reference data (synthetic)" },
        ...(bank ? [{ label: "Analyst evidence", value: bank.label + (bank.detail ? ` · ${bank.detail}` : ""), source: evidenceSource(bank) }] : []),
      ],
    },
    {
      id: "transaction_plausibility",
      name: "Transaction Plausibility",
      description: "Purchase order, pricing and transaction size",
      status: statusFor(poPoints),
      points: poPoints,
      summary:
        po === undefined
          ? "Pricing is normal, but the purchase order could not be verified."
          : po.value === true
            ? "Purchase order on file; pricing and size are normal."
            : "No purchase order available to support the transaction.",
      checks: [
        { label: "Purchase order / contract", ...poCheck },
        { label: "Unit price vs benchmark", result: "pass", detail: `Website design £450/day within ${REFERENCE.marketBenchmark}` },
        { label: "Transaction size", result: "pass", detail: `${money(amount, currency)} within seller's typical ${REFERENCE.typicalInvoiceValue}` },
        { label: "Round-number anomaly", result: "pass", detail: "Line amounts are not suspiciously round" },
      ],
      evidence: [
        { label: "PO on invoice", value: fx.po_reference.value ?? "Not stated", source: "Uploaded document" },
        ...(po ? [{ label: "Analyst evidence", value: po.label + (po.detail ? ` · ${po.detail}` : ""), source: evidenceSource(po) }] : []),
      ],
    },
    {
      id: "relationship",
      name: "Buyer–Seller Relationship",
      description: "Related parties, history and behaviour change",
      status: "clear",
      points: 0,
      summary: `Established relationship: ${REFERENCE.priorInvoicesBetweenParties} prior invoices since ${REFERENCE.sellerSince}.`,
      checks: [
        { label: "Related-party indicators", result: "pass", detail: "No shared directors or addresses" },
        { label: "Transaction history", result: "pass", detail: `${REFERENCE.priorInvoicesBetweenParties} invoices settled since ${REFERENCE.sellerSince}` },
        { label: "Behaviour change", result: "pass", detail: "Invoice frequency and size consistent" },
      ],
      evidence: [{ label: "Relationship record", value: "6 invoices · no related-party flags", source: "Reference data (synthetic)" }],
    },
    {
      id: "payment_behaviour",
      name: "Payment Behaviour",
      description: "Buyer's historical lateness, defaults and disputes",
      status: statusFor(POINTS.paymentLate),
      points: POINTS.paymentLate,
      summary: `${p.late} of ${p.invoices} past invoices paid late (avg ${p.avgDaysLate} days); no defaults.`,
      checks: [
        { label: "Historical lateness", result: "warn", detail: `${p.late} late payments, average ${p.avgDaysLate} days` },
        { label: "Defaults", result: "pass", detail: "None recorded" },
        { label: "Disputes", result: "pass", detail: "None recorded" },
      ],
      evidence: [{ label: "Payment history", value: `${p.invoices} invoices · ${p.onTime} on time · ${p.late} late`, source: "Reference data (synthetic)" }],
    },
    {
      id: "duplicate_financing",
      name: "Duplicate Financing",
      description: "Duplicate invoices and previously financed receivables",
      status: "clear",
      points: 0,
      summary: "No duplicate or previously financed invoice found.",
      checks: [
        { label: "Exact duplicate", result: "pass", detail: "INV-2026-014 not in invoice history" },
        { label: "Near-duplicate number", result: "pass", detail: "No similar number with the same amount" },
        { label: "Previously financed", result: "pass", detail: "Not in financing history (internal only)" },
      ],
      evidence: [{ label: "Financing history search", value: "0 matches", source: "Reference data (synthetic)" }],
    },
  ];

  for (const m of modules) m.evidence.push(...docsFor(m.id));

  const score = Math.min(100, modules.reduce((s, m) => s + m.points, 0));
  const band = bandFor(score);
  const recommendation = RECOMMENDATION[band];
  const advanceRate = band === "low" ? ADVANCE_RATE_LOW : null;

  // ---- Drivers: plain-English reasons + what to check ----
  const drivers: RiskDriver[] = [];
  if (bank === undefined) {
    drivers.push({
      id: "bank_changed",
      moduleId: "seller_verification",
      title: "Bank details changed",
      explanation: `The payment destination (${fx.bank_account.value ?? "—"}) differs from the seller's previously verified account (${REFERENCE.sellerAccountOnFile}).`,
      points: bankPoints,
      whatToCheck: [
        "Confirm the change directly with the seller using contact details from your records, not the invoice.",
        "Request proof of account ownership (bank letter or statement header).",
        "Check when the change first appeared compared with previous invoices.",
      ],
    });
  } else if (bank.value === false) {
    drivers.push({
      id: "bank_not_notified",
      moduleId: "seller_verification",
      title: "Unannounced bank account change",
      explanation: "The seller never notified a change of account. This is the most common pattern in invoice redirection (business email compromise) fraud.",
      points: bankPoints,
      whatToCheck: [
        "Do not release funds to the new account.",
        "Call the seller on a known number and ask whether they issued this invoice.",
        "Check the sender address of the email that delivered the invoice.",
      ],
    });
  }
  if (po === undefined || po.value === false) {
    drivers.push({
      id: "po_unverified",
      moduleId: "transaction_plausibility",
      title: po === undefined ? "Purchase order not verified" : "No purchase order available",
      explanation: `The invoice cites ${fx.po_reference.value ?? "no PO"}, which isn't in the buyer's records. Without it, there's no independent proof the buyer ordered these services.`,
      points: poPoints,
      whatToCheck: [
        "Request the PO or signed contract from the seller.",
        "Confirm delivery or service completion with the buyer.",
        "Note the PO reference was hard to read: check for an O / 0 mix-up.",
      ],
    });
  }
  drivers.push({
    id: "late_payments",
    moduleId: "payment_behaviour",
    title: "Buyer has paid late before",
    explanation: `${p.late} of the buyer's last ${p.invoices} invoices were paid late (average ${p.avgDaysLate} days). No defaults.`,
    points: POINTS.paymentLate,
    whatToCheck: ["Allow for a short delay in the repayment schedule.", "Check for any open disputes with the buyer."],
  });
  drivers.sort((a, b) => b.points - a.points);

  // ---- Completeness: unknown is never treated as safe ----
  const items: CompletenessItem[] = [
    { id: "invoice_details", label: "Invoice details", status: "verified", note: "Extracted and reviewed", moduleId: null },
    { id: "buyer_identity", label: "Buyer identity", status: "verified", note: "Registry match", moduleId: null },
    { id: "seller_identity", label: "Seller identity", status: "verified", note: "Registry match", moduleId: null },
    { id: "payment_history", label: "Historical payments", status: "verified", note: "12 invoices on record", moduleId: null },
    { id: "duplicate_search", label: "Duplicate financing search", status: "verified", note: "Internal history searched", moduleId: null },
    {
      id: "bank_change",
      label: "Bank account change",
      status: bank === undefined ? "missing" : "verified",
      note:
        bank === undefined ? "Not yet confirmed with the seller"
        : bankDocumented ? `Document · ${bank.detail}`
        : bank.value === true ? `Confirmed by analyst · ${bank.detail}`
        : "Analyst: change was not notified",
      moduleId: bank === undefined ? "seller_verification" : null,
    },
    {
      id: "purchase_order",
      label: "Purchase order",
      status: po?.value === true ? "verified" : "missing",
      note: po === undefined ? "Not found in buyer records" : po.value === true ? `Supplied · ${po.detail}` : "Analyst has no PO or contract",
      moduleId: po?.value === true ? null : "transaction_plausibility",
    },
  ];
  const percent = Math.round((items.filter((i) => i.status === "verified").length / items.length) * 100);

  return {
    id: meta.id,
    version: meta.version,
    createdAt: new Date().toISOString(),
    invoice,
    score,
    band,
    recommendation,
    advanceRate,
    financingAmount: advanceRate !== null && amount !== null ? Math.round(amount * advanceRate) : null,
    modules,
    drivers,
    completeness: { percent, items },
    evidence,
    preliminary: percent < 100,
    previous: meta.previous,
  };
}

export function snapshot(a: Assessment): AssessmentSnapshot {
  const modulePoints = {} as Record<ModuleId, number>;
  const moduleSummaries = {} as Record<ModuleId, string>;
  for (const m of a.modules) {
    modulePoints[m.id] = m.points;
    moduleSummaries[m.id] = m.summary;
  }
  return { version: a.version, score: a.score, band: a.band, recommendation: a.recommendation, modulePoints, moduleSummaries };
}
