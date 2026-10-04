import { CircleCheck, Circle } from "lucide-react";
import type { Assessment, ModuleId } from "@/lib/types";

/** Assessment completeness: what is verified, what still needs information. */
export default function MissingInformation({ a, onResolve }: { a: Assessment; onResolve: (m: ModuleId) => void }) {
  const verified = a.completeness.items.filter((i) => i.status === "verified");
  const missing = a.completeness.items.filter((i) => i.status === "missing");

  return (
    <section className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="font-semibold">Assessment completeness</h2>
        <span className="num text-sm text-muted">{a.completeness.percent}%</span>
      </div>
      <div className="mt-3 h-1.5 rounded-full bg-surface-2 overflow-hidden">
        <div className="h-full bg-accent transition-all duration-700" style={{ width: `${a.completeness.percent}%` }} />
      </div>

      {missing.length > 0 && (
        <>
          <div className="mt-5 text-xs uppercase tracking-wider text-faint">Needs information</div>
          <ul className="mt-2 space-y-2">
            {missing.map((i) => (
              <li key={i.id} className="flex items-center gap-2 text-sm">
                <Circle size={14} className="text-warn shrink-0" />
                <span className="flex-1 min-w-0">
                  {i.label}
                  <span className="block text-xs text-muted">{i.note}</span>
                </span>
                {i.moduleId && (
                  <button
                    type="button"
                    onClick={() => onResolve(i.moduleId!)}
                    className="text-xs font-medium border border-line-strong bg-bg rounded-md px-2.5 py-1 hover:border-accent hover:text-accent"
                  >
                    Add evidence
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      <div className="mt-5 text-xs uppercase tracking-wider text-faint">Verified</div>
      <ul className="mt-2 space-y-1.5">
        {verified.map((i) => (
          <li key={i.id} className="flex items-center gap-2 text-sm">
            <CircleCheck size={14} className="text-ok shrink-0" />
            <span>{i.label}</span>
            <span className="text-xs text-faint truncate">· {i.note}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
