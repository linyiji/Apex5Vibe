import { ArrowRight, Info } from "lucide-react";
import RiskScore from "./RiskScore";
import { BAND_TEXT, RECOMMENDATION_LABEL, money, parseAmount } from "@/lib/format";
import type { Assessment } from "@/lib/types";

const RECOMMENDATION_SUB = {
  eligible: "Can be financed at the standard advance rate",
  manual_review: "An analyst should review before financing",
  decline: "Significant risk: do not finance as is",
};

export default function AssessmentSummary({ a }: { a: Assessment }) {
  const f = a.invoice.fields;
  const cur = f.currency.value;
  const missing = a.completeness.items.filter((i) => i.status === "missing").length;

  return (
    <section>
      {/* Invoice identity */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-sm text-muted">Invoice {f.invoice_number.value ?? "—"}</div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-lg font-medium">
            {f.seller.value ?? "Unknown seller"} <ArrowRight size={16} className="text-faint" /> {f.buyer.value ?? "Unknown buyer"}
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-semibold num tracking-tight">{money(parseAmount(f.amount.value), cur)}</div>
          <div className="text-xs text-muted mt-1">
            {a.preliminary ? "Preliminary assessment" : "Assessment complete"} · version {a.version}
          </div>
        </div>
      </div>

      {/* Key figures */}
      <div className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-x-5 border-y border-line">
        <div className="py-5">
          <div className="text-xs uppercase tracking-wider text-muted mb-2">Finance</div>
          <div className={`text-3xl font-semibold tracking-tight ${BAND_TEXT[a.band]}`}>{RECOMMENDATION_LABEL[a.recommendation]}</div>
          <div className="text-sm text-muted mt-1">{RECOMMENDATION_SUB[a.recommendation]}</div>
        </div>
        <div className="py-5 lg:pl-5 lg:border-l border-line">
          <div className="text-xs uppercase tracking-wider text-muted mb-2">Risk score</div>
          <RiskScore key={a.id} score={a.score} band={a.band} from={a.previous?.score} />
        </div>
        <div className="py-5 max-lg:border-t lg:pl-5 lg:border-l border-line">
          <div className="text-xs uppercase tracking-wider text-muted mb-2">Advance</div>
          {a.advanceRate !== null ? (
            <>
              <div className="text-3xl font-semibold num tracking-tight">{Math.round(a.advanceRate * 100)}%</div>
              <div className="text-sm text-muted mt-1 num">{money(a.financingAmount, cur)} financing</div>
            </>
          ) : (
            <>
              <div className="text-3xl font-semibold text-muted">{a.recommendation === "decline" ? "None" : "Pending"}</div>
              <div className="text-sm text-muted mt-1">{a.recommendation === "decline" ? "Not offered at this risk level" : "Set after analyst review"}</div>
            </>
          )}
        </div>
        <div className="py-5 max-lg:border-t lg:pl-5 lg:border-l border-line">
          <div className="text-xs uppercase tracking-wider text-muted mb-2">Information completeness</div>
          <div className="text-3xl font-semibold num tracking-tight">{a.completeness.percent}%</div>
          <div className="mt-2 h-1.5 rounded-full bg-surface-2 overflow-hidden">
            <div className="h-full bg-accent transition-all duration-700" style={{ width: `${a.completeness.percent}%` }} />
          </div>
          <div className="text-sm text-muted mt-1.5">
            {missing ? `${missing} important item${missing > 1 ? "s" : ""} missing` : "All key items verified"}
          </div>
        </div>
      </div>

      {a.preliminary && (
        <p className="mt-4 flex items-start gap-2 text-sm text-warn">
          <Info size={16} className="mt-0.5 shrink-0" />
          <span>
            <strong className="font-medium">Preliminary assessment.</strong> Additional information could materially change this score.
            Unknown items are counted as risk, not treated as safe.
          </span>
        </p>
      )}
    </section>
  );
}
