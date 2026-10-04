import { Check, CircleHelp, TriangleAlert, X } from "lucide-react";
import type { CheckResult, RiskModule } from "@/lib/types";

const RESULT: Record<CheckResult, { icon: typeof Check; cls: string }> = {
  pass: { icon: Check, cls: "text-ok" },
  warn: { icon: TriangleAlert, cls: "text-warn" },
  fail: { icon: X, cls: "text-risk" },
  unknown: { icon: CircleHelp, cls: "text-warn" },
};

/** Expanded view of one module: every check it ran, and the evidence behind it. */
export default function EvidencePanel({ module: m }: { module: RiskModule }) {
  return (
    <div className="grid md:grid-cols-2 gap-6 pt-1 pb-5 pl-8 text-sm">
      <div>
        <div className="text-xs uppercase tracking-wider text-faint mb-2">Checks</div>
        <ul className="space-y-2">
          {m.checks.map((c) => {
            const { icon: Icon, cls } = RESULT[c.result];
            return (
              <li key={c.label} className="flex gap-2">
                <Icon size={15} className={`mt-0.5 shrink-0 ${cls}`} />
                <span>
                  <span className="font-medium">{c.label}</span>
                  <span className="block text-muted">{c.detail}</span>
                </span>
              </li>
            );
          })}
        </ul>
      </div>
      <div>
        <div className="text-xs uppercase tracking-wider text-faint mb-2">Evidence</div>
        <dl className="space-y-2">
          {m.evidence.map((e) => (
            <div key={e.label} className="rounded-lg bg-surface border border-line px-3 py-2">
              <dt className="text-xs text-muted">{e.label}</dt>
              <dd className="num">{e.value}</dd>
              <dd className="text-[11px] text-faint mt-0.5">Source: {e.source}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
