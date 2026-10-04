"use client";

import { useRef, useState } from "react";
import { FileText, NotebookPen, Paperclip, RefreshCw, X } from "lucide-react";
import type { Assessment, ModuleId } from "@/lib/types";

const DOC_ACCEPT = ".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.csv";

const PLACEHOLDER: Partial<Record<ModuleId, string>> = {
  seller_verification: "e.g. Supplier emailed on 2 Oct confirming the new account; called their finance team on the number on file.",
  transaction_plausibility: "e.g. PO attached. Buyer confirmed the website was delivered on 10 Sep.",
  payment_behaviour: "e.g. The two late payments were during the buyer's system migration in 2025.",
};

interface Props {
  a: Assessment;
  moduleId: ModuleId;
  onModuleChange: (id: ModuleId) => void;
  submitting: boolean;
  onSubmit: (note: string, files: File[]) => Promise<boolean>;
}

/** Analyst notes + documents for one risk area, sent for AI review and reassessment. */
export default function AnalystInput({ a, moduleId, onModuleChange, submitting, onSubmit }: Props) {
  const [note, setNote] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const input = useRef<HTMLInputElement>(null);

  // What the analyst actually sent (not the evidence derived from it).
  const submitted = a.evidence.filter((e) => e.field === "analyst_note" || e.source === "upload");
  const moduleName = (id: ModuleId) => a.modules.find((m) => m.id === id)?.name ?? id;
  const moduleOf = (field: string, value: boolean | string): ModuleId =>
    field === "po_provided" ? "transaction_plausibility" : field === "bank_account_change_confirmed" ? "seller_verification" : (value as ModuleId);
  const canSend = (note.trim() || files.length) && !submitting;

  async function send() {
    if (!canSend) return;
    if (await onSubmit(note.trim(), files)) {
      setNote("");
      setFiles([]);
    }
  }

  return (
    <section id="analyst-input" className="rounded-2xl border border-line bg-surface p-5 scroll-mt-24">
      <h2 className="font-semibold flex items-center gap-2"><NotebookPen size={17} className="text-accent" /> Analyst notes &amp; documents</h2>
      <p className="mt-1 text-xs text-muted">Add what you&apos;ve verified. It&apos;s sent to the AI analyst, which updates the evidence and recalculates the score.</p>

      <label className="block mt-4 text-xs text-muted mb-1.5" htmlFor="analyst-module">Risk area</label>
      <select
        id="analyst-module"
        value={moduleId}
        onChange={(e) => onModuleChange(e.target.value as ModuleId)}
        className="w-full bg-bg border border-line rounded-lg px-2.5 py-2 text-sm outline-none focus:border-accent"
      >
        {a.modules.map((m) => (
          <option key={m.id} value={m.id}>{m.name}{m.points ? ` (+${m.points})` : ""}</option>
        ))}
      </select>

      <label className="block mt-4 text-xs text-muted mb-1.5" htmlFor="analyst-note">Note</label>
      <textarea
        id="analyst-note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={4}
        placeholder={PLACEHOLDER[moduleId] ?? "What did you check, and what did you find?"}
        className="w-full bg-bg border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-accent placeholder:text-faint resize-y"
      />

      {files.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {files.map((f, i) => (
            <li key={f.name + i} className="flex items-center gap-2 text-sm rounded-lg border border-line bg-bg px-2.5 py-1.5">
              <FileText size={14} className="text-accent shrink-0" />
              <span className="flex-1 truncate">{f.name}</span>
              <button type="button" aria-label={`Remove ${f.name}`} onClick={() => setFiles((fs) => fs.filter((_, j) => j !== i))} className="text-faint hover:text-text">
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => input.current?.click()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-line-strong px-3 py-2 text-sm hover:border-accent hover:text-accent"
        >
          <Paperclip size={14} /> Attach files
        </button>
        <button
          type="button"
          disabled={!canSend}
          onClick={send}
          className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-accent text-bg font-semibold px-3 py-2 text-sm hover:brightness-110 disabled:opacity-40"
        >
          <RefreshCw size={14} className={submitting ? "animate-spin" : ""} /> Send &amp; reassess
        </button>
        <input
          ref={input}
          type="file"
          multiple
          className="hidden"
          accept={DOC_ACCEPT}
          onChange={(e) => {
            const picked = Array.from(e.target.files ?? []);
            e.target.value = "";
            setFiles((fs) => [...fs, ...picked]);
          }}
        />
      </div>
      <p className="mt-2 text-[11px] text-faint">Prototype: documents count by file name and notes are read with simple rules. The AI analyst will read the real contents once the backend is connected.</p>

      {submitted.length > 0 && (
        <div className="mt-5 pt-4 border-t border-line">
          <div className="text-xs uppercase tracking-wider text-faint mb-2">Submitted</div>
          <ul className="space-y-2">
            {submitted.map((e) => (
              <li key={e.addedAt + e.field + e.detail} className="text-sm">
                <span className="flex items-center gap-1.5">
                  {e.source === "upload" ? <FileText size={13} className="text-accent shrink-0" /> : <NotebookPen size={13} className="text-accent shrink-0" />}
                  <span className="truncate">{e.detail}</span>
                </span>
                <span className="block pl-5 text-xs text-faint">{moduleName(moduleOf(e.field, e.value))} · {e.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
