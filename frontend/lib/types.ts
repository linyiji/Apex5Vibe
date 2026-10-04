// Current frontend prototype contracts (docs/02-current-api.md).
// These differ from the workspace backend's /v1 contract; see docs/03-backend-integration.md.

// ---------- Extraction ----------

export type FieldStatus = "extracted" | "uncertain" | "missing" | "edited";

export type InvoiceFieldKey =
  | "seller"
  | "buyer"
  | "buyer_registration"
  | "invoice_number"
  | "invoice_date"
  | "due_date"
  | "amount"
  | "currency"
  | "bank_account"
  | "po_reference";

export interface InvoiceField {
  value: string | null;
  status: FieldStatus;
  /** Short snippet of the document text the value came from. */
  source: string | null;
}

export interface LineItem {
  description: string;
  quantity: number | null;
  unit_price: number | null;
  amount: number | null;
}

export interface ExtractedInvoice {
  file_name: string;
  /** True when the values are demo values, not read from the uploaded file. */
  simulated: boolean;
  fields: Record<InvoiceFieldKey, InvoiceField>;
  line_items: LineItem[];
}

// ---------- Assessment ----------

export type RiskBand = "low" | "medium" | "high";
export type ModuleStatus = "clear" | "watch" | "risk";
export type CheckResult = "pass" | "warn" | "fail" | "unknown";

export interface ModuleCheck {
  label: string;
  result: CheckResult;
  detail: string;
}

export interface ModuleEvidence {
  label: string;
  value: string;
  source: string;
}

export type ModuleId =
  | "invoice_integrity"
  | "buyer_verification"
  | "seller_verification"
  | "transaction_plausibility"
  | "relationship"
  | "payment_behaviour"
  | "duplicate_financing";

export interface RiskModule {
  id: ModuleId;
  name: string;
  description: string;
  status: ModuleStatus;
  points: number;
  summary: string;
  checks: ModuleCheck[];
  evidence: ModuleEvidence[];
}

/** A plain-English reason the score is elevated, with what the analyst should check. */
export interface RiskDriver {
  id: string;
  moduleId: ModuleId;
  title: string;
  explanation: string;
  points: number;
  whatToCheck: string[];
}

export interface CompletenessItem {
  id: string;
  label: string;
  status: "verified" | "missing";
  /** How it was verified, or why it matters if missing. */
  note: string;
  /** The risk area to add notes / documents to when this item is missing. */
  moduleId: ModuleId | null;
}

export type EvidenceSource = "analyst_note" | "upload" | "reference_data";
export type EvidenceConfidence = "user_provided" | "document" | "verified";

export interface EvidenceItem {
  field: string;
  value: boolean | string;
  label: string;
  detail: string;
  source: EvidenceSource;
  confidence: EvidenceConfidence;
  addedAt: string;
}

export type Recommendation = "eligible" | "manual_review" | "decline";

export interface AssessmentSnapshot {
  version: number;
  score: number;
  band: RiskBand;
  recommendation: Recommendation;
  modulePoints: Record<ModuleId, number>;
  moduleSummaries: Record<ModuleId, string>;
}

export interface Assessment {
  id: string;
  version: number;
  createdAt: string;
  invoice: ExtractedInvoice;
  score: number;
  band: RiskBand;
  recommendation: Recommendation;
  /** 0–1, null when financing is not offered at this band. */
  advanceRate: number | null;
  financingAmount: number | null;
  modules: RiskModule[];
  drivers: RiskDriver[];
  completeness: { percent: number; items: CompletenessItem[] };
  evidence: EvidenceItem[];
  /** True while important information is missing: the score may change. */
  preliminary: boolean;
  /** The previous version, present after a reassessment. */
  previous: AssessmentSnapshot | null;
}

// ---------- Analyst input ----------

/** What the analyst sends for one risk area: a note and/or documents. Triggers a reassessment. */
export interface AnalystSubmission {
  assessmentId: string;
  moduleId: ModuleId;
  note: string;
  files: File[];
}
