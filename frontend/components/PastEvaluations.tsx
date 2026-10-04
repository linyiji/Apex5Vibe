"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, ChevronRight } from "lucide-react";
import { listCases, type CaseState } from "@/lib/case-store";
import { BAND_LABEL, BAND_TEXT, RECOMMENDATION_LABEL, money, parseAmount } from "@/lib/format";

function timeAgo(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  return hrs < 24 ? `${hrs} hr ago` : new Date(iso).toLocaleDateString("en-GB");
}

/** Assessments run in this browser session. Real entries only: starts empty. */
export default function PastEvaluations() {
  const [cases, setCases] = useState<CaseState[] | null>(null);

  useEffect(() => {
    let alive = true;
    listCases().then((c) => alive && setCases(c));
    return () => { alive = false; };
  }, []);

  if (cases === null) return null; // not loaded yet (session storage is client-only)

  return (
    <section className="mt-14">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Past evaluations</h2>
        <span className="text-xs text-faint">This browser session</span>
      </div>

      {cases.length === 0 ? (
        <p className="mt-3 text-sm text-muted border-t border-line pt-4">
          No evaluations yet. Assessments you run will appear here so you can reopen them.
        </p>
      ) : (
        <ul className="mt-3 border-t border-line">
          {cases.map((c) => {
            const f = c.invoice.fields;
            const s = c.summary;
            return (
              <li key={c.id} className="border-b border-line">
                <Link href={`/assessment/${c.id}`} className="flex items-center gap-4 py-3.5 px-1 hover:bg-surface/60">
                  <span className={`w-12 text-right text-xl font-semibold num ${s ? BAND_TEXT[s.band] : "text-faint"}`}>
                    {s ? s.score : "—"}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="flex items-center gap-1.5 text-sm font-medium truncate">
                      {f.seller.value ?? "Unknown seller"} <ArrowRight size={12} className="text-faint shrink-0" /> {f.buyer.value ?? "Unknown buyer"}
                    </span>
                    <span className="block text-xs text-muted truncate">
                      {f.invoice_number.value ?? "No invoice number"} · {money(parseAmount(f.amount.value), f.currency.value)} · {timeAgo(c.updatedAt)}
                    </span>
                  </span>
                  <span className="hidden sm:block text-right text-xs">
                    {s ? (
                      <>
                        <span className={`block font-medium ${BAND_TEXT[s.band]}`}>{RECOMMENDATION_LABEL[s.recommendation]}</span>
                        <span className="block text-faint">
                          {BAND_LABEL[s.band]} · {s.completeness}% complete
                          {s.version > 1 && ` · ${s.firstScore} → ${s.score} after ${s.version - 1} reassessment${s.version > 2 ? "s" : ""}`}
                        </span>
                      </>
                    ) : (
                      <span className="text-warn">Awaiting review</span>
                    )}
                  </span>
                  <ChevronRight size={16} className="text-faint" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
