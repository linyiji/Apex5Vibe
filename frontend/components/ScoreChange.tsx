import { ArrowRight, Sparkles } from "lucide-react";
import { BAND_LABEL, BAND_TEXT } from "@/lib/format";
import type { Assessment } from "@/lib/types";

/** "23 → 9, Medium → Low, −14 points" plus a per-module before/after. */
export default function ScoreChange({ a }: { a: Assessment }) {
  const prev = a.previous;
  if (!prev) return null;
  const delta = a.score - prev.score;
  const changed = a.modules.filter((m) => prev.modulePoints[m.id] !== m.points);

  return (
    <section className="rounded-2xl border border-accent/30 bg-accent/[0.04] p-6 fade-up" aria-live="polite">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
        <div className="flex items-center gap-3 text-3xl font-semibold num">
          <span className={BAND_TEXT[prev.band]}>{prev.score}</span>
          <ArrowRight className="text-faint" />
          <span className={BAND_TEXT[a.band]}>{a.score}</span>
        </div>
        <div className="text-sm">
          <span className={BAND_TEXT[prev.band]}>{BAND_LABEL[prev.band]}</span>
          <span className="text-faint"> → </span>
          <span className={BAND_TEXT[a.band]}>{BAND_LABEL[a.band]}</span>
        </div>
        <div className={`text-sm font-semibold num ${delta < 0 ? "text-ok" : delta > 0 ? "text-risk" : "text-muted"}`}>
          {delta > 0 ? "+" : delta < 0 ? "−" : ""}
          {Math.abs(delta)} points
        </div>
      </div>

      {changed.length === 0 && (
        <p className="mt-4 text-sm text-muted">
          No module score changed. Your submission is on the record in the module&apos;s evidence, but it didn&apos;t resolve a risk check.
        </p>
      )}

      {changed.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-muted mb-3">What changed?</h3>
          <div className="space-y-3">
            {changed.map((m) => (
              <div key={m.id} className="grid sm:grid-cols-[180px_1fr_1fr] gap-3 text-sm">
                <div className="font-medium">{m.name}</div>
                <div className="rounded-lg bg-surface border border-line p-3">
                  <div className="text-xs text-faint mb-1">Before</div>
                  <div className="text-muted">{prev.moduleSummaries[m.id]}</div>
                  <div className="mt-1 num text-muted">+{prev.modulePoints[m.id]} risk</div>
                </div>
                <div className="rounded-lg bg-surface border border-line-strong p-3">
                  <div className="text-xs text-faint mb-1">After</div>
                  <div>{m.summary}</div>
                  <div className={`mt-1 num ${m.points < prev.modulePoints[m.id] ? "text-ok" : "text-risk"}`}>+{m.points} risk</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="mt-5 flex items-center gap-2 text-xs text-muted">
        <Sparkles size={13} className="text-accent" /> Assessment updated using the analyst notes and documents submitted.
      </p>
    </section>
  );
}
