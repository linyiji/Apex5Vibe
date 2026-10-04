"use client";

import { useState } from "react";
import { ChevronRight, CircleCheck, TriangleAlert, OctagonAlert } from "lucide-react";
import EvidencePanel from "./EvidencePanel";
import { STATUS_TEXT } from "@/lib/format";
import type { RiskModule } from "@/lib/types";

const ICON = { clear: CircleCheck, watch: TriangleAlert, risk: OctagonAlert };
const LABEL = { clear: "Clear", watch: "Watch", risk: "Risk" };

/** One assessment module as an expandable row: status, contribution, summary, evidence. */
export default function RiskFactorCard({ module: m, changed }: { module: RiskModule; changed?: boolean }) {
  const [open, setOpen] = useState(m.status === "risk");
  const Icon = ICON[m.status];

  return (
    <div className={`border-b border-line ${changed ? "bg-accent/[0.03]" : ""}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center gap-3 py-4 text-left hover:bg-surface/60 px-1"
      >
        <Icon size={18} className={`shrink-0 ${STATUS_TEXT[m.status]}`} />
        <span className="flex-1 min-w-0">
          <span className="font-medium">{m.name}</span>
          {changed && <span className="ml-2 text-[11px] text-accent">updated</span>}
          <span className="block text-sm text-muted truncate">{m.summary}</span>
        </span>
        <span className={`text-xs ${STATUS_TEXT[m.status]} hidden sm:inline w-12 text-right`}>{LABEL[m.status]}</span>
        <span className={`num text-sm w-10 text-right ${m.points ? STATUS_TEXT[m.status] : "text-faint"}`}>+{m.points}</span>
        <ChevronRight size={16} className={`text-faint transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && <EvidencePanel module={m} />}
    </div>
  );
}
