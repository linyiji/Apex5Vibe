"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Info, Loader2 } from "lucide-react";
import DecisionView from "@/components/DecisionView";
import InvoiceFieldsForm from "@/components/InvoiceFieldsForm";
import InvoicePreview from "@/components/InvoicePreview";
import ProcessingState, { ASSESSMENT_STEPS } from "@/components/ProcessingState";
import StepIndicator from "@/components/StepIndicator";
import { getAssessment, runAssessment } from "@/lib/api";
import { getCase, getPreview, recordResult, updateCase, type CaseState } from "@/lib/case-store";
import type { Assessment, InvoiceFieldKey } from "@/lib/types";
import { API_MODE } from "@/lib/runtime-config";
import AssessmentWorkspace from "@/components/live/AssessmentWorkspace";

type Stage = "loading" | "missing" | "review" | "processing" | "decision";

async function loadCase(id: string): Promise<{ c: CaseState | null; a: Assessment | null }> {
  const c = getCase(id);
  if (!c?.assessmentId) return { c, a: null };
  const a = await getAssessment(c.assessmentId).catch(() => null);
  return { c, a };
}

function MockAssessmentPage() {
  const { id } = useParams<{ id: string }>();
  const [stage, setStage] = useState<Stage>("loading");
  const [caseState, setCaseState] = useState<CaseState | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [run, setRun] = useState<Promise<Assessment> | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load the case from session state (client-only, so it runs after mount).
  useEffect(() => {
    let alive = true;
    loadCase(id).then(({ c, a }) => {
      if (!alive) return;
      setCaseState(c);
      setAssessment(a);
      setStage(!c ? "missing" : a ? "decision" : "review");
    });
    return () => { alive = false; };
  }, [id]);

  // Keep the "Past evaluations" summary in step with the latest (re)assessment.
  useEffect(() => {
    if (assessment) recordResult(id, assessment);
  }, [id, assessment]);

  function editField(key: InvoiceFieldKey, value: string) {
    if (!caseState) return;
    const invoice = {
      ...caseState.invoice,
      fields: { ...caseState.invoice.fields, [key]: { ...caseState.invoice.fields[key], value: value || null, status: "edited" as const } },
    };
    setCaseState(updateCase(caseState.id, { invoice }));
  }

  function startAssessment() {
    if (!caseState) return;
    setError(null);
    const p = runAssessment(caseState.invoice);
    p.catch(() => {}); // handled in finishAssessment
    setRun(p);
    setStage("processing");
  }

  const finishAssessment = useCallback(async () => {
    if (!run || !caseState) return;
    try {
      const a = await run;
      setCaseState(updateCase(caseState.id, { assessmentId: a.id, summary: null }));
      setAssessment(a);
      setStage("decision");
    } catch (e) {
      setError(e instanceof Error ? e.message : "The assessment failed. Try again.");
      setStage("review");
    }
  }, [run, caseState]);

  if (stage === "loading") {
    return <div className="py-24 grid place-items-center text-muted"><Loader2 className="animate-spin" /></div>;
  }

  if (stage === "missing" || !caseState) {
    return (
      <div className="max-w-md mx-auto py-24 text-center">
        <h1 className="text-xl font-semibold">Assessment not found</h1>
        <p className="mt-2 text-muted text-sm">It may have expired with your browser session.</p>
        <Link href="/" className="mt-6 inline-block rounded-lg bg-accent text-bg font-semibold px-5 py-2.5">Start a new assessment</Link>
      </div>
    );
  }

  if (stage === "processing") {
    return (
      <>
        <StepIndicator current={3} />
        <ProcessingState title="Assessing invoice…" steps={ASSESSMENT_STEPS} onDone={finishAssessment} />
      </>
    );
  }

  if (stage === "decision" && assessment) {
    return (
      <>
        <StepIndicator current={4} />
        <DecisionView assessment={assessment} onAssessment={setAssessment} />
      </>
    );
  }

  // Review
  const inv = caseState.invoice;
  return (
    <>
      <StepIndicator current={2} />
      <div className="grid lg:grid-cols-2 gap-10 items-start">
        <div>
          <h2 className="text-sm font-medium text-muted mb-3 truncate">{inv.file_name}</h2>
          <InvoicePreview invoice={inv} preview={getPreview(caseState.id)} />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Invoice details</h1>
          <p className="mt-1 text-sm text-muted">Check what was extracted and correct anything that&apos;s wrong before the assessment runs.</p>
          {inv.simulated && (
            <p className="mt-4 flex items-start gap-2 text-sm text-warn">
              <Info size={16} className="mt-0.5 shrink-0" />
              Simulated extraction: no backend is connected, so these are demo values, not read from your file.
            </p>
          )}
          <div className="mt-6">
            <InvoiceFieldsForm fields={inv.fields} onChange={editField} />
          </div>
          {error && <p className="mt-4 text-sm text-risk" role="alert">{error}</p>}
          <div className="mt-8 flex justify-end gap-3">
            <Link href="/" className="rounded-lg border border-line px-5 py-2.5 text-muted hover:text-text">Back</Link>
            <button type="button" onClick={startAssessment} className="rounded-lg bg-accent text-bg font-semibold px-6 py-2.5 hover:brightness-110">
              Run Assessment
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default function AssessmentPage() {
  const { id } = useParams<{ id: string }>();
  return API_MODE === "live" ? <AssessmentWorkspace key={id} caseId={id} /> : <MockAssessmentPage />;
}
