// Client-side state for one assessment "case": the invoice being reviewed,
// the backend assessment id once it exists, and a summary for "Past evaluations".
// This is UI state, not backend data, so it lives in sessionStorage.

import type { Assessment, ExtractedInvoice, Recommendation, RiskBand } from "./types";

/** Latest result, kept for the "Past evaluations" list. */
export interface CaseSummary {
  score: number;
  band: RiskBand;
  recommendation: Recommendation;
  version: number;
  firstScore: number;
  completeness: number;
}

export interface CaseState {
  id: string;
  invoice: ExtractedInvoice;
  assessmentId: string | null;
  createdAt: string;
  updatedAt: string;
  summary: CaseSummary | null;
}

const KEY = "apexvibe.cases";
// Object URLs for uploaded files can't be stored; they only live in this tab's memory.
const previews: Record<string, { url: string; kind: "pdf" | "image" }> = {};

function load(): Record<string, CaseState> {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

function save(all: Record<string, CaseState>) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable */
  }
}

const memory: Record<string, CaseState> = {};

export function createCase(invoice: ExtractedInvoice, file?: File): string {
  const id = `case-${Date.now().toString(36)}`;
  const now = new Date().toISOString();
  const c: CaseState = { id, invoice, assessmentId: null, createdAt: now, updatedAt: now, summary: null };
  memory[id] = c;
  save({ ...load(), [id]: c });
  if (file) previews[id] = { url: URL.createObjectURL(file), kind: file.type === "application/pdf" || /\.pdf$/i.test(file.name) ? "pdf" : "image" };
  return id;
}

export function getCase(id: string): CaseState | null {
  return memory[id] ?? load()[id] ?? null;
}

export function updateCase(id: string, patch: Partial<CaseState>): CaseState | null {
  const current = getCase(id);
  if (!current) return null;
  const next = { ...current, ...patch, updatedAt: new Date().toISOString() };
  memory[id] = next;
  save({ ...load(), [id]: next });
  return next;
}

/** Records the latest assessment result on the case. */
export function recordResult(id: string, a: Assessment) {
  const current = getCase(id);
  if (!current) return;
  const firstScore = current.summary && current.assessmentId === a.id ? current.summary.firstScore : a.score;
  updateCase(id, {
    summary: { score: a.score, band: a.band, recommendation: a.recommendation, version: a.version, firstScore, completeness: a.completeness.percent },
  });
}

/** All cases in this browser session, newest activity first. */
export async function listCases(): Promise<CaseState[]> {
  const all = { ...load(), ...memory };
  return Object.values(all)
    .filter((c) => c.createdAt)
    .sort((x, y) => y.updatedAt.localeCompare(x.updatedAt));
}

export function getPreview(id: string) {
  return previews[id] ?? null;
}
