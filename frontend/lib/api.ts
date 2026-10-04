// Original browser-only prototype; explicitly enabled with NEXT_PUBLIC_API_MODE=mock.
// Live traffic uses backend-api.ts and the generated /v1 contract.

import { computeAssessment, snapshot } from "./mock-engine";
import { interpretSubmission } from "./mock-notes";
import { demoInvoice } from "./mock-data";
import type { AnalystSubmission, Assessment, ExtractedInvoice } from "./types";

import { API_MODE } from "./runtime-config";

function requireMock() {
  if (API_MODE !== "mock") throw new Error("The simulated prototype is disabled. Use the /v1 workspace in Live mode.");
}

// ---------------------------------------------------------------------------
// Mock backend: state kept in sessionStorage so a page refresh survives.
// ---------------------------------------------------------------------------

const STORE_KEY = "apexvibe.mock.assessments";
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function loadStore(): Record<string, Assessment> {
  try {
    return JSON.parse(sessionStorage.getItem(STORE_KEY) || "{}");
  } catch {
    return {};
  }
}
function saveAssessment(a: Assessment) {
  try {
    const store = loadStore();
    store[a.id] = a;
    sessionStorage.setItem(STORE_KEY, JSON.stringify(store));
  } catch {
    /* storage unavailable: state lives only in the current page */
  }
  memory[a.id] = a;
}
const memory: Record<string, Assessment> = {};
function mockGet(id: string): Assessment {
  const a = memory[id] ?? loadStore()[id];
  if (!a) throw new Error("Assessment not found. It may have expired. Start a new assessment.");
  return a;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Sends the document for AI extraction. POST /api/invoices/extract */
export async function extractInvoice(file: File): Promise<ExtractedInvoice> {
  requireMock();
  await delay(1100);
  // Mock: no document is read; demo values are returned and labelled as simulated.
  return demoInvoice(file.name, true);
}

/** Loads the built-in demo invoice (no upload). */
export async function loadDemoInvoice(): Promise<ExtractedInvoice> {
  requireMock();
  await delay(500);
  return demoInvoice();
}

/** Runs all seven modules. POST /api/assessments */
export async function runAssessment(invoice: ExtractedInvoice): Promise<Assessment> {
  requireMock();
  await delay(400);
  const id = `ASM-${Math.floor(1000 + Math.random() * 9000)}`;
  const a = computeAssessment(invoice, [], { id, version: 1, previous: null });
  saveAssessment(a);
  return a;
}

/** GET /api/assessments/:id */
export async function getAssessment(id: string): Promise<Assessment> {
  requireMock();
  return mockGet(id);
}

/**
 * Sends the analyst's note and documents for one risk area; the backend AI reads them,
 * updates the evidence and re-runs the scoring. Returns the new assessment version.
 * POST /api/assessments/:id/reassess (multipart: module_id, note, files[])
 */
export async function submitAnalystInput(s: AnalystSubmission): Promise<Assessment> {
  requireMock();
  await delay(300);
  const current = mockGet(s.assessmentId);
  const added = interpretSubmission(s.moduleId, s.note, s.files.map((f) => f.name));
  const next = computeAssessment(current.invoice, [...current.evidence, ...added], {
    id: current.id,
    version: current.version + 1,
    previous: snapshot(current),
  });
  saveAssessment(next);
  return next;
}
