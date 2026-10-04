"use client";

import { useCallback, useRef, useState } from "react";
import AnalystInput from "./AnalystInput";
import AssessmentSummary from "./AssessmentSummary";
import MissingInformation from "./MissingInformation";
import ProcessingState, { REASSESS_STEPS } from "./ProcessingState";
import RiskDrivers from "./RiskDrivers";
import RiskFactorCard from "./RiskFactorCard";
import ScoreChange from "./ScoreChange";
import { submitAnalystInput } from "@/lib/api";
import type { Assessment, ModuleId } from "@/lib/types";

interface Props {
  assessment: Assessment;
  onAssessment: (a: Assessment) => void;
}

/** The decision screen: results on the left, completeness + analyst notes on the right. */
export default function DecisionView({ assessment: a, onAssessment }: Props) {
  const riskiest = [...a.modules].sort((x, y) => y.points - x.points)[0].id;
  const [moduleId, setModuleId] = useState<ModuleId>(riskiest);
  const [reassessing, setReassessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const call = useRef<Promise<Assessment> | null>(null);
  const done = useRef<(ok: boolean) => void>(() => {});

  /** Jump to the notes box with a risk area pre-selected. */
  function addEvidenceFor(m: ModuleId) {
    setModuleId(m);
    document.getElementById("analyst-input")?.scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => document.getElementById("analyst-note")?.focus({ preventScroll: true }), 400);
  }

  // Starts the API call and the processing animation together; resolves when both finish.
  function submit(note: string, files: File[]): Promise<boolean> {
    setError(null);
    setReassessing(true);
    call.current = submitAnalystInput({ assessmentId: a.id, moduleId, note, files });
    call.current.catch(() => {}); // handled in finish
    return new Promise((resolve) => { done.current = resolve; });
  }

  const finish = useCallback(async () => {
    try {
      const next = await call.current!;
      onAssessment(next);
      window.scrollTo({ top: 0, behavior: "smooth" });
      done.current(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reassessment failed. Try again.");
      done.current(false);
    } finally {
      setReassessing(false);
    }
  }, [onAssessment]);

  const changedIds = new Set(a.previous ? a.modules.filter((m) => a.previous!.modulePoints[m.id] !== m.points).map((m) => m.id) : []);
  const sortedModules = [...a.modules].sort((x, y) => y.points - x.points);

  return (
    <>
      {reassessing && (
        <div className="fixed inset-0 z-50 bg-bg/85 backdrop-blur-sm grid place-items-center px-4">
          <div className="w-full max-w-md rounded-2xl border border-line bg-surface px-6">
            <ProcessingState title="Reassessing invoice…" steps={REASSESS_STEPS} stepMs={450} onDone={finish} />
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-[minmax(0,1fr)_380px] gap-10 items-start">
        <div className="space-y-10 min-w-0">
          <AssessmentSummary a={a} />
          <ScoreChange key={a.version} a={a} />
          <RiskDrivers a={a} onAddEvidence={addEvidenceFor} />

          <section>
            <div className="flex items-baseline justify-between">
              <h2 className="text-xl font-semibold tracking-tight">Why this score</h2>
              <span className="text-xs text-muted">7 independent modules · click to see evidence</span>
            </div>
            <div className="mt-3 border-t border-line">
              {sortedModules.map((m) => (
                <RiskFactorCard key={`${m.id}-${a.version}`} module={m} changed={changedIds.has(m.id)} />
              ))}
            </div>
            <div className="mt-3 flex justify-between text-sm px-1">
              <span className="text-muted">Total risk score (sum of modules, max 100)</span>
              <span className="num font-semibold">{a.score} / 100</span>
            </div>
            <p className="mt-2 px-1 text-xs text-faint">Bands: low 0–10 · medium 11–25 · high above 25. Demo thresholds, not a validated credit policy.</p>
          </section>
        </div>

        <aside className="space-y-6">
          <MissingInformation a={a} onResolve={addEvidenceFor} />
          <AnalystInput a={a} moduleId={moduleId} onModuleChange={setModuleId} submitting={reassessing} onSubmit={submit} />
          {error && <p className="text-sm text-risk" role="alert">{error}</p>}
        </aside>
      </div>
    </>
  );
}
