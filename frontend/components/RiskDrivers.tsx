import { NotebookPen } from "lucide-react";
import type { Assessment, ModuleId } from "@/lib/types";

/** Plain-English drivers of an elevated score, each with what to check. Medium/high only. */
export default function RiskDrivers({ a, onAddEvidence }: { a: Assessment; onAddEvidence: (m: ModuleId) => void }) {
  if (a.band === "low") return null;
  const drivers = a.drivers.filter((d) => d.points >= 3);
  if (!drivers.length) return null;

  return (
    <section>
      <h2 className="text-xl font-semibold tracking-tight">Why might this be high risk?</h2>
      <div className="mt-4 divide-y divide-line border-y border-line">
        {drivers.map((d) => (
          <article key={d.id} className="py-5 grid md:grid-cols-[1fr_1fr] gap-x-8 gap-y-3">
            <div>
              <h3 className="font-medium flex items-center gap-2">
                <span className={`num text-sm ${d.points >= 10 ? "text-risk" : "text-warn"}`}>+{d.points}</span>
                {d.title}
              </h3>
              <p className="mt-1.5 text-sm text-muted leading-relaxed">{d.explanation}</p>
              <button
                type="button"
                onClick={() => onAddEvidence(d.moduleId)}
                className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-line-strong bg-surface px-2.5 py-1 text-xs font-medium hover:border-accent hover:text-accent"
              >
                <NotebookPen size={13} /> Add note or document
              </button>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider text-faint mb-2">What to check</div>
              <ul className="space-y-1.5 text-sm">
                {d.whatToCheck.map((s) => (
                  <li key={s} className="flex gap-2"><span className="text-accent">›</span>{s}</li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
