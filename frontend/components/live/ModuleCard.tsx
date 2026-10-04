"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Paperclip, RotateCw, X } from "lucide-react";
import { ApiError, backend } from "@/lib/backend-api";
import {
  MODULE_NAMES,
  validateFiles,
  type Capabilities,
  type EventPage,
  type Module,
  type RunDetail,
} from "@/lib/backend-types";
import { button, control, primary } from "./PartyPicker";

function ModuleDetail({
  module,
  close,
}: {
  module: Module;
  close: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [run, setRun] = useState<RunDetail | null>(null);
  const [events, setEvents] = useState<EventPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  useEffect(() => {
    let active = true;
    backend
      .events(module.case_id)
      .then((data) => {
        if (active) setEvents(data);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [module.case_id]);
  async function showRun(id: string) {
    try {
      setRun(await backend.run(module.case_id, module.module_key, id));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run unavailable.");
    }
  }
  async function moreEvents() {
    if (!events) return;
    try {
      const next = await backend.events(module.case_id, events.next_after_seq);
      setEvents({ ...next, items: [...events.items, ...next.items] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "History unavailable.");
    }
  }
  const output = run ? run.output : module.current_run;
  return (
    <dialog
      ref={dialog}
      onClose={close}
      aria-labelledby={`detail-${module.module_key}`}
      className="fixed inset-0 m-auto w-[1000px] max-w-[90vw] max-h-[88vh] rounded-2xl border border-line bg-surface text-text p-0 backdrop:bg-black/65"
    >
      <div className="sticky top-0 bg-surface border-b border-line p-5 flex items-center justify-between z-10">
        <div>
          <p className="text-xs text-accent uppercase tracking-widest">
            Module full view
          </p>
          <h2
            id={`detail-${module.module_key}`}
            className="text-xl font-semibold"
          >
            {MODULE_NAMES[module.module_key]}
          </h2>
        </div>
        <button className={button} aria-label="Close full view" onClick={close}>
          <X size={18} />
        </button>
      </div>
      <div className="p-6 space-y-6">
        {error && (
          <p role="alert" className="text-risk">
            {error}
          </p>
        )}
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div>
            AI score{" "}
            <strong className="block text-2xl">
              {output?.ai_score ?? "—"}
            </strong>
          </div>
          <div>
            Manual adjustment{" "}
            <strong className="block text-2xl">
              {module.effective_adjustment > 0 ? "+" : ""}
              {module.effective_adjustment}
            </strong>
          </div>
          <div>
            Module final{" "}
            <strong className="block text-2xl">
              {module.final_score ?? "—"} / {module.cap}
            </strong>
          </div>
        </div>
        {run && (
          <p className="text-warn text-sm">
            Viewing a historical AI run. Manual adjustment and module final
            above refer to the latest module state.
          </p>
        )}
        <p className="text-sm text-muted">
          {output?.summary ?? "No successful analysis yet."}
        </p>
        <section>
          <h3 className="font-medium mb-3">Findings and sources</h3>
          <div className="space-y-3">
            {output?.findings.map((finding, index) => (
              <div
                key={index}
                className="rounded-lg bg-bg border border-line p-3 text-sm"
              >
                <p>{finding.statement}</p>
                <ul className="mt-2 text-xs text-muted space-y-1">
                  {finding.source_refs.map((source, n) => (
                    <li className="break-all" key={n}>
                      {source.source_id} · {source.locator}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3 className="font-medium mb-3">All evidence versions</h3>
          <div className="space-y-2">
            {module.evidence.map((evidence) => (
              <div
                key={evidence.evidence_id}
                className="border border-line rounded-lg p-3 text-sm"
              >
                <div className="flex justify-between gap-3">
                  {evidence.file_id ? (
                    <a
                      href={backend.fileUrl(module.case_id, evidence.file_id)}
                      className="text-accent break-all"
                    >
                      {evidence.filename}
                    </a>
                  ) : (
                    <span>{evidence.source_id}</span>
                  )}
                  <span className="text-muted shrink-0">
                    {evidence.status} · {evidence.parse_status}
                    {evidence.version ? ` · v${evidence.version}` : ""}
                  </span>
                </div>
                {evidence.supersedes_evidence_id && (
                  <p className="text-xs text-muted mt-1 break-all">
                    Replaces {evidence.supersedes_evidence_id}
                  </p>
                )}
                {evidence.error && (
                  <p className="text-risk mt-1">
                    {evidence.error.error.message}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3 className="font-medium mb-2">Supplementary information</h3>
          {module.supplements.length ? (
            module.supplements.map((note) => (
              <div
                className="bg-bg rounded-lg p-3 mt-2"
                key={note.supplement_id}
              >
                <p className="whitespace-pre-wrap text-sm">{note.text}</p>
                <p className="text-xs text-muted mt-1">
                  {note.author_id} ·{" "}
                  {new Date(note.created_at).toLocaleString("en-GB")}
                </p>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">No supplementary information.</p>
          )}
        </section>
        <section>
          <h3 className="font-medium mb-2">Manual adjustment history</h3>
          {module.manual_adjustments.map((adjustment) => (
            <p
              className="text-sm text-muted mt-2"
              key={adjustment.adjustment_id}
            >
              Requested {adjustment.requested_adjustment}, effective{" "}
              {adjustment.effective_adjustment} · {adjustment.status} ·{" "}
              {adjustment.reason}
            </p>
          ))}
          {!module.manual_adjustments.length && (
            <p className="text-sm text-muted">No manual adjustments.</p>
          )}
        </section>
        <section>
          <h3 className="font-medium mb-2">AI run history</h3>
          <div className="flex flex-wrap gap-2">
            {module.run_history.map((item, index) => (
              <button
                key={item.run_id}
                className={button}
                onClick={() => showRun(item.run_id)}
              >
                Run {index + 1} · {item.status} · {item.ai_score ?? "—"} pts
              </button>
            ))}
          </div>
          {run && (
            <details className="mt-3">
              <summary className="cursor-pointer text-sm text-accent">
                Audit input, model response and provenance
              </summary>
              <pre className="mt-2 bg-bg p-3 rounded-lg text-xs max-h-96 overflow-auto whitespace-pre-wrap break-all">
                {JSON.stringify(run, null, 2)}
              </pre>
            </details>
          )}
        </section>
        <section>
          <h3 className="font-medium mb-2">State history</h3>
          <ol className="text-xs text-muted space-y-2">
            {events?.items
              .filter(
                (event) =>
                  event.module_key === module.module_key || !event.module_key,
              )
              .map((event) => (
                <li key={event.event_id}>
                  {new Date(event.occurred_at).toLocaleString("en-GB")} ·{" "}
                  {event.type.replaceAll("_", " ")}
                </li>
              ))}
          </ol>
          {events && (
            <button onClick={moreEvents} className={`${button} mt-3`}>
              Load more history
            </button>
          )}
        </section>
      </div>
    </dialog>
  );
}

export default function ModuleCard({
  module,
  capabilities,
  refresh,
  connected,
}: {
  module: Module;
  capabilities: Capabilities;
  refresh: () => Promise<unknown>;
  connected: boolean;
}) {
  const name = MODULE_NAMES[module.module_key];
  const [expanded, setExpanded] = useState(false);
  const [full, setFull] = useState(false);
  const [note, setNote] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [group, setGroup] = useState("");
  const [replaceId, setReplaceId] = useState("");
  const [adjustment, setAdjustment] = useState("0");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const current = module.freshness === "current";
  const allowed = (action: Module["allowed_actions"][number]) =>
    connected && module.allowed_actions.includes(action);
  const activeSheet = module.evidence.find(
    (e) => e.evidence_group === "invoice_field_sheet" && e.status === "active",
  );
  const pendingFile = module.evidence.some((e) => e.parse_status === "pending");
  const state = pendingFile
    ? "Parsing evidence"
    : module.state === "running"
      ? "AI processing"
      : module.state === "queued"
        ? "Queued"
        : module.state === "failed"
          ? "Failed"
          : module.state === "needs_info"
            ? "Needs information"
            : !current && module.current_run
              ? "New evidence · stale"
              : module.state === "succeeded"
                ? "Completed"
                : "Not started";
  async function perform(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
    } catch (e) {
      const message = e instanceof Error ? e.message : "The operation failed.";
      setError(
        e instanceof ApiError && e.status === 409
          ? `${message} Your draft is preserved. Review the refreshed module and submit again.`
          : message,
      );
      await refresh().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }
  async function save(rerun: boolean) {
    await perform(async () => {
      let version = module.module_version;
      let savedFile = false;
      if (files.length) {
        validateFiles(files, capabilities);
        if (group && files.length !== 1)
          throw new Error("Select one invoice field sheet per version.");
        if (group && activeSheet && replaceId !== activeSheet.evidence_id)
          throw new Error(
            "Explicitly select the current field sheet to replace before submitting a correction.",
          );
        await backend.evidence(
          module.case_id,
          module.module_key,
          version,
          files,
          rerun && !note.trim(),
          group || undefined,
          replaceId || undefined,
        );
        savedFile = true;
        setFiles([]);
        setReplaceId("");
        if (fileInput.current) fileInput.current.value = "";
        version = (await backend.module(module.case_id, module.module_key))
          .module_version;
      }
      if (note.trim()) {
        try {
          await backend.supplement(
            module.case_id,
            module.module_key,
            version,
            note.trim(),
            rerun,
          );
          setNote("");
        } catch (e) {
          if (savedFile)
            setNotice(
              "Files were saved. The note is still in your draft; submit it again after reviewing the refreshed state.",
            );
          throw e;
        }
      }
      setNotice(
        rerun
          ? "Evidence saved. This module will update when its AI run completes."
          : "Information saved. Re-run this module when ready.",
      );
    });
  }
  return (
    <article
      className="border border-line bg-surface rounded-xl overflow-hidden"
      data-module={module.module_key}
    >
      <div className="p-5 flex justify-between gap-5 items-start">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-base">{name}</h3>
            <span className={`text-xs ${current ? "text-ok" : "text-warn"}`}>
              {state}
            </span>
            {module.state === "running" && (
              <Loader2 size={14} className="text-accent animate-spin" />
            )}
          </div>
          <p className="mt-2 text-sm text-muted leading-relaxed line-clamp-2">
            {module.current_run?.summary ??
              module.error?.error.message ??
              "Awaiting assessment."}
          </p>
          <div className="flex gap-3 text-xs text-muted mt-3">
            <span>AI {module.current_run?.ai_score ?? "—"}</span>
            <span>
              Manual {module.effective_adjustment > 0 ? "+" : ""}
              {module.effective_adjustment}
            </span>
            <span>
              {module.evidence.filter((e) => e.status === "active").length}{" "}
              active sources
            </span>
            {module.adjustment_status === "pending_review" && (
              <span className="text-warn">Adjustment needs confirmation</span>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div
            className={`text-2xl font-semibold num ${current && (module.final_score ?? 0) > 0 ? "text-warn" : "text-text"}`}
          >
            {module.final_score ?? "—"}
            <span className="text-xs text-muted font-normal">
              {" "}
              / {module.cap}
            </span>
          </div>
          {!current && module.current_run && (
            <p className="text-xs text-warn">Previous score</p>
          )}
          <button
            type="button"
            className="text-xs text-accent mt-2 hover:underline"
            onClick={() => setFull(true)}
          >
            Full view
          </button>
        </div>
      </div>
      {module.error && (
        <p role="alert" className="mx-5 mb-3 text-sm text-risk">
          {module.error.error.message}
        </p>
      )}
      <div className="px-5 pb-4 flex gap-2">
        <button
          type="button"
          className={button}
          onClick={() => setExpanded(!expanded)}
        >
          <Paperclip size={14} className="inline mr-2" />
          {expanded ? "Hide inputs" : "Add note or document"}
        </button>
        <button
          type="button"
          className={button}
          disabled={
            busy || !allowed("rerun") || !!note.trim() || !!files.length
          }
          onClick={() =>
            perform(async () => {
              await backend.rerun(
                module.case_id,
                module.module_key,
                module.module_version,
              );
            })
          }
        >
          <RotateCw size={13} className="inline mr-2" />
          Re-run AI
        </button>
      </div>
      {expanded && (
        <div className="border-t border-line p-5 bg-bg/50 space-y-4">
          <label className="block text-sm">
            Supplementary information
            <textarea
              aria-label={`Supplementary information for ${name}`}
              value={note}
              maxLength={10000}
              onChange={(e) => setNote(e.target.value)}
              className={`${control} mt-2 min-h-24`}
              placeholder="Add facts, explanations or analyst notes…"
              disabled={busy}
            />
          </label>
          <div className="text-sm">
            <p>Attach files</p>
            <input
              id={`files-${module.module_key}`}
              aria-label={`Attach files to ${name}`}
              ref={fileInput}
              type="file"
              multiple
              accept={capabilities.formats
                .filter((f) => f.status === "ready")
                .map((f) => f.extension)
                .join(",")}
              disabled={busy || !allowed("upload_evidence")}
              onChange={(e) => {
                const selected = Array.from(e.target.files ?? []);
                setFiles(selected);
                setReplaceId("");
                setGroup(
                  module.module_key === "invoice_integrity" &&
                    selected.length === 1 &&
                    selected[0].name.toLowerCase().endsWith(".xlsx")
                    ? "invoice_field_sheet"
                    : "",
                );
              }}
              className="hidden"
            />
            <button
              type="button"
              className={`${button} mt-2`}
              disabled={busy || !allowed("upload_evidence")}
              onClick={() => fileInput.current?.click()}
            >
              Choose files
            </button>
            {files.length === 0 && (
              <span className="text-xs text-muted ml-3">No files selected</span>
            )}
          </div>
          <p className="text-xs text-muted">
            PDF, XLSX, CSV · {capabilities.max_file_bytes / 1024 / 1024} MiB per
            file · up to {capabilities.max_files_per_request} files. Selecting a
            file does not change the score.
          </p>
          {files.length > 0 && (
            <p className="text-xs text-accent break-all">
              Selected: {files.map((f) => f.name).join(", ")}
            </p>
          )}
          {module.module_key === "invoice_integrity" && files.length > 0 && (
            <div className="space-y-3">
              <label className="text-sm block">
                Evidence type
                <select
                  aria-label="Evidence type"
                  className={`${control} mt-1`}
                  value={group}
                  onChange={(e) => {
                    setGroup(e.target.value);
                    setReplaceId("");
                  }}
                >
                  <option value="">General supporting evidence</option>
                  <option value="invoice_field_sheet">
                    Invoice field sheet (versioned XLSX)
                  </option>
                </select>
              </label>
              {group && activeSheet && (
                <label className="flex gap-2 items-start text-sm text-warn">
                  <input
                    type="checkbox"
                    aria-label="Replace current field sheet"
                    checked={replaceId === activeSheet.evidence_id}
                    onChange={(e) =>
                      setReplaceId(
                        e.target.checked ? activeSheet.evidence_id : "",
                      )
                    }
                    className="mt-1"
                  />
                  <span>
                    Replace current field sheet: {activeSheet.filename} (v
                    {activeSheet.version}). The old version stays in history.
                  </span>
                </label>
              )}
            </div>
          )}
          <div className="flex gap-3">
            <button
              type="button"
              className={button}
              disabled={
                busy ||
                !allowed("save_information") ||
                (!note.trim() && !files.length)
              }
              onClick={() => save(false)}
            >
              Save only
            </button>
            <button
              type="button"
              className={primary}
              disabled={
                busy ||
                !allowed("save_and_rerun") ||
                (!note.trim() && !files.length)
              }
              onClick={() => save(true)}
            >
              {busy ? "Saving…" : "Send & reassess"}
            </button>
          </div>
          <details className="border-t border-line pt-4">
            <summary className="text-sm cursor-pointer text-muted">
              Manual adjustment
            </summary>
            <p className="text-xs text-muted mt-2">
              Positive increases risk; negative reduces it. The original AI
              score is retained.
            </p>
            <div className="grid grid-cols-[100px_1fr_auto] gap-3 mt-3">
              <input
                aria-label={`Manual adjustment for ${name}`}
                type="number"
                min={-module.cap}
                max={module.cap}
                step="1"
                className={control}
                value={adjustment}
                onChange={(e) => setAdjustment(e.target.value)}
              />
              <input
                aria-label={`Adjustment reason for ${name}`}
                placeholder="Reason (required)"
                className={control}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <button
                type="button"
                className={button}
                disabled={
                  busy ||
                  !allowed("adjust") ||
                  !reason.trim() ||
                  !adjustment.trim()
                }
                onClick={() =>
                  perform(async () => {
                    const value = Number(adjustment);
                    if (
                      !Number.isInteger(value) ||
                      Math.abs(value) > module.cap
                    )
                      throw new Error(
                        `Enter a whole number between -${module.cap} and ${module.cap}.`,
                      );
                    if (!module.current_run) return;
                    await backend.adjust(
                      module.case_id,
                      module.module_key,
                      module.module_version,
                      module.current_run.run_id,
                      value,
                      reason.trim(),
                    );
                    setReason("");
                    setNotice("Adjustment saved with its reason and AI run.");
                  })
                }
              >
                Apply adjustment
              </button>
            </div>
          </details>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-risk px-5 pb-4">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="text-sm text-accent px-5 pb-4">
          {notice}
        </p>
      )}
      {full && <ModuleDetail module={module} close={() => setFull(false)} />}
    </article>
  );
}
