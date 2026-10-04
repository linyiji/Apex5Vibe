"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { backend } from "@/lib/backend-api";
import {
  amount,
  MODULE_NAMES,
  validateFiles,
  type Capabilities,
  type PartyResolution,
  type Workspace,
} from "@/lib/backend-types";
import { useWorkspace } from "@/lib/use-workspace";
import InvoiceDocument from "./InvoiceDocument";
import ModuleCard from "./ModuleCard";
import { button, primary } from "./PartyPicker";

function parties(workspace: Workspace): PartyResolution[] {
  return workspace.parties.filter(
    (party): party is PartyResolution => "side" in party,
  );
}

export default function AssessmentWorkspace({ caseId }: { caseId: string }) {
  const {
    workspace: ws,
    previous,
    error: connectionError,
    refresh,
  } = useWorkspace(caseId);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const replacementInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    backend
      .capabilities(controller.signal)
      .then(setCapabilities)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, []);
  async function action(operation: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await operation();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The operation failed.");
      await refresh().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }
  const errors = (
    <>
      {connectionError && (
        <p
          role="alert"
          className="mb-5 rounded-lg border border-risk/40 bg-risk/5 p-4 text-sm text-risk"
        >
          {connectionError} Actions are paused until the connection returns.
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="mb-5 rounded-lg border border-risk/40 p-4 text-sm text-risk"
        >
          {error}
        </p>
      )}
    </>
  );
  if (!ws)
    return (
      <div className="py-20 max-w-xl mx-auto text-center">
        {errors}
        {!connectionError && (
          <Loader2 className="animate-spin mx-auto text-accent" />
        )}
        <p className="text-muted mt-4">
          {connectionError
            ? "This case could not be loaded."
            : "Loading saved case…"}
        </p>
        <Link className="inline-block mt-5 text-accent" href="/">
          Return to queue
        </Link>
      </div>
    );
  const runningInitial = ws.initial_assessment_status === "running";
  const result =
    ws.navigation.target === "result" &&
    ws.initial_assessment_status === "settled";
  const invoice = ws.invoice;
  const resolvedParties = parties(ws);
  const conflict = resolvedParties.some((p) => p.status === "conflict");
  const current = ws.aggregate.current_result;
  const last = ws.aggregate.last_valid_result;
  const decision = ws.aggregate.decision;
  const validCount = ws.modules.filter(
    (m) => m.state === "succeeded" && m.freshness === "current",
  ).length;
  const scoreChange =
    current && previous
      ? current.final_risk_score - previous.final_risk_score
      : 0;
  const decisionLabel =
    decision.status === "eligible"
      ? "Eligible for financing"
      : decision.status === "manual_review"
        ? "Manual review required"
        : "Financing pending";

  async function replace(file: File) {
    if (!capabilities) return;
    await action(async () => {
      validateFiles([file], capabilities, true);
      await backend.uploadInvoice(
        caseId,
        ws!.case_revision,
        file,
        !!ws!.invoice,
      );
    });
  }

  if (runningInitial)
    return (
      <div>
        {errors}
        <StepIndicator current={3} />
        <div className="max-w-2xl mx-auto py-8">
          <p className="text-accent text-xs uppercase tracking-widest">
            Live assessment
          </p>
          <h1 className="text-3xl font-semibold mt-2">Assessing invoice…</h1>
          <p className="text-muted mt-3">
            Each module evaluates its own evidence. Results open automatically
            when the initial assessment finishes.
          </p>
          <ol className="mt-7 space-y-3">
            {ws.modules.map((module) => (
              <li
                key={module.module_key}
                className="flex justify-between items-center rounded-xl border border-line bg-surface p-4"
              >
                <span>{MODULE_NAMES[module.module_key]}</span>
                <span
                  className={`flex gap-2 items-center text-sm ${module.state === "succeeded" ? "text-ok" : module.state === "failed" || module.state === "needs_info" ? "text-risk" : "text-muted"}`}
                >
                  {module.state === "running" ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : module.state === "succeeded" ? (
                    <CheckCircle2 size={16} />
                  ) : null}
                  {module.state.replaceAll("_", " ")}
                </span>
              </li>
            ))}
          </ol>
          <p className="mt-5 text-xs text-muted">
            You can return to the queue; this case continues on the server.
          </p>
          <Link href="/" className="inline-block mt-3 text-sm text-accent">
            Back to queue
          </Link>
        </div>
      </div>
    );

  if (!result)
    return (
      <div>
        {errors}
        <StepIndicator
          current={ws.stage === "extracting" || !invoice ? 1 : 2}
        />
        {ws.stage === "extracting" || !invoice ? (
          <div className="max-w-xl mx-auto py-12 text-center">
            <h1 className="text-2xl font-semibold">
              {ws.error
                ? "Invoice needs attention"
                : ws.stage === "extracting"
                  ? "Reading the invoice…"
                  : "Upload an invoice"}
            </h1>
            {ws.stage === "extracting" && (
              <Loader2 className="animate-spin text-accent mx-auto mt-6" />
            )}
            <p className="text-muted mt-4">
              {ws.error?.error.message ??
                (ws.stage === "extracting"
                  ? "Extracting the form fields and resolving buyer and seller."
                  : "This case is saved. Choose an invoice PDF to continue.")}
            </p>
            {ws.stage !== "extracting" && (
              <div className="mt-5">
                <button
                  className={button}
                  disabled={busy || !capabilities || !!connectionError}
                  onClick={() => replacementInput.current?.click()}
                >
                  Choose another invoice PDF
                </button>
                <input
                  ref={replacementInput}
                  aria-label="Retry invoice upload"
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  disabled={busy || !capabilities || !!connectionError}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void replace(file);
                  }}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-[1fr_1fr] gap-8 items-start">
            <InvoiceDocument
              caseId={caseId}
              fileId={invoice.source_refs[0].source_id}
            />
            <section>
              <h1 className="text-2xl font-semibold">Review invoice details</h1>
              <p className="mt-2 text-sm text-muted">
                Read from the uploaded PDF. To correct these fields, upload a
                replacement invoice.
              </p>
              <dl className="mt-5 grid grid-cols-2 gap-x-5 gap-y-4 text-sm">
                {[
                  ["Invoice number", invoice.invoice_number],
                  ["Invoice amount", amount(invoice.total, invoice.currency)],
                  ["Invoice date", invoice.invoice_date],
                  ["Due date", invoice.due_date],
                  ["Seller", invoice.seller.legal_name],
                  ["Buyer", invoice.buyer.legal_name],
                  ["Payment terms", invoice.payment_terms],
                  ["Product", invoice.line_items[0]?.sku],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-muted text-xs">{label}</dt>
                    <dd className="mt-1 break-words">{value}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-6 space-y-3">
                {resolvedParties.map((party) => (
                  <div
                    key={party.side}
                    className={`rounded-lg border p-3 text-sm ${party.status === "conflict" ? "border-risk/50 bg-risk/5" : "border-line bg-surface"}`}
                  >
                    <div className="flex justify-between gap-2">
                      <strong className="capitalize">{party.side}</strong>
                      <span
                        className={
                          party.status === "conflict" ? "text-risk" : "text-ok"
                        }
                      >
                        {party.status}
                      </span>
                    </div>
                    <p className="mt-1">{party.invoice_entity.legal_name}</p>
                    <p className="text-xs text-muted mt-1">
                      {party.invoice_entity.tax_id} ·{" "}
                      {party.invoice_entity.country}
                    </p>
                    {party.status === "conflict" && (
                      <div className="mt-3">
                        <p className="text-risk text-xs mb-2">
                          The selected company differs from the invoice. Resolve
                          this before assessment.
                        </p>
                        <button
                          disabled={busy || !!connectionError}
                          className={button}
                          onClick={() =>
                            action(() =>
                              backend.resolve(
                                caseId,
                                ws.case_revision,
                                party.side,
                                party.selection,
                                "use_invoice_entity",
                              ),
                            )
                          }
                        >
                          Use invoice {party.side}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div className="mt-6 flex justify-between items-center gap-3">
                <Link href="/" className={button}>
                  Back
                </Link>
                <button
                  disabled={busy || conflict || !!connectionError || !!ws.error}
                  className={primary}
                  onClick={() =>
                    action(() => backend.start(caseId, ws.case_revision))
                  }
                >
                  {busy ? "Starting…" : "Run Assessment"}
                </button>
              </div>
              <details className="mt-5 text-xs text-muted">
                <summary className="cursor-pointer">
                  Replace main invoice
                </summary>
                <button
                  className={`${button} mt-3`}
                  disabled={busy || !capabilities || !!connectionError}
                  onClick={() => replacementInput.current?.click()}
                >
                  Choose replacement PDF
                </button>
                <input
                  aria-label="Replace invoice PDF"
                  id="replace-invoice-file"
                  ref={replacementInput}
                  className="hidden"
                  type="file"
                  accept=".pdf"
                  disabled={busy || !!connectionError}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void replace(file);
                  }}
                />
              </details>
            </section>
          </div>
        )}
      </div>
    );

  return (
    <div>
      {errors}
      <StepIndicator current={4} />
      <div className="flex justify-between gap-5 items-start mb-6">
        <div>
          <p className="text-xs text-accent uppercase tracking-widest">
            Assessment result
          </p>
          <h1 className="text-3xl font-semibold mt-1">
            {invoice?.invoice_number ?? "Invoice assessment"}
          </h1>
          <p className="text-muted text-sm mt-2">
            {invoice?.seller.legal_name} → {invoice?.buyer.legal_name}
          </p>
        </div>
        <Link href="/" className={button}>
          Back to queue
        </Link>
      </div>
      <div className="grid grid-cols-4 gap-4 mb-5">
        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-xs text-muted">Invoice risk index</h2>
          <div className="flex items-end gap-2 mt-3">
            <strong
              data-testid="risk-score"
              className={`text-4xl num ${current?.risk_band === "HIGH" ? "text-risk" : current?.risk_band === "LOW" ? "text-ok" : "text-muted"}`}
            >
              {current?.final_risk_score ?? "Pending"}
            </strong>
            {current && (
              <span className="text-sm text-muted pb-1">
                / 100 · {current.risk_band}
              </span>
            )}
          </div>
          <p className="text-xs text-muted mt-3">
            Higher means more risk · Low &lt; 30
          </p>
        </section>
        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-xs text-muted">Financing decision</h2>
          <p
            data-testid="financing-decision"
            className={`mt-3 font-semibold text-xl ${decision.status === "eligible" ? "text-ok" : "text-warn"}`}
          >
            {decisionLabel}
          </p>
          <p className="text-xs text-muted mt-3">
            {decision.status === "manual_review"
              ? "No automatic financing approval"
              : decision.status === "pending"
                ? "Wait for current evidence and any adjustment review"
                : "Current low risk, no blocking findings"}
          </p>
        </section>
        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-xs text-muted">Indicative advance</h2>
          <p
            data-testid="advance-amount"
            className="mt-3 font-semibold text-xl num"
          >
            {amount(decision.advance_amount, decision.currency)}
          </p>
          <p className="text-xs text-muted mt-3">
            {decision.advance_rate != null
              ? `${decision.advance_rate * 100}% of ${amount(invoice?.total, invoice?.currency)}`
              : "No current financing amount"}
          </p>
        </section>
        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-xs text-muted">Assessment completeness</h2>
          <p className="mt-3 font-semibold text-2xl num">{validCount} / 7</p>
          <p className="text-xs text-muted mt-3">
            Modules with a current successful analysis
          </p>
        </section>
      </div>
      {!current && (
        <div
          role="status"
          className="mb-5 rounded-xl border border-warn/30 bg-warn/5 p-4 text-sm text-warn"
        >
          <strong>Current assessment {ws.aggregate.status}.</strong> Evidence is
          being assessed or needs attention.{" "}
          {last && (
            <span>
              Previous result: {last.final_risk_score} / 100 {last.risk_band}.
              It is historical and does not authorize financing.
            </span>
          )}
        </div>
      )}
      {current && previous && previous.snapshot_id !== current.snapshot_id && (
        <p
          role="status"
          data-testid="score-change"
          className={`mb-5 rounded-xl border p-4 text-sm ${scoreChange < 0 ? "border-ok/30 bg-ok/5 text-ok" : scoreChange > 0 ? "border-risk/30 bg-risk/5 text-risk" : "border-accent/30 bg-accent/5 text-accent"}`}
        >
          {scoreChange < 0
            ? `Risk decreased by ${-scoreChange} points`
            : scoreChange > 0
              ? `Risk increased by ${scoreChange} points`
              : "Risk score unchanged"}
          :{" "}
          <strong className="num">
            {previous.final_risk_score} → {current.final_risk_score}
          </strong>{" "}
          · {previous.risk_band} → {current.risk_band}. The total reflects
          current module scores and reviewed adjustments.
        </p>
      )}
      {decision.reasons.some(
        (reason) => !["current_low_risk", "high_risk_score"].includes(reason),
      ) && (
        <p className="text-xs text-warn mb-5">
          Decision status:{" "}
          {decision.reasons
            .map((reason) => reason.replaceAll("_", " "))
            .join("; ")}
        </p>
      )}
      <div className="grid grid-cols-[minmax(0,1fr)_270px] gap-6 items-start">
        <section className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Assessment modules</h2>
            <span className="text-xs text-muted">
              AI score + manual adjustment
            </span>
          </div>
          {capabilities ? (
            ws.modules.map((module) => (
              <ModuleCard
                key={module.module_key}
                module={module}
                capabilities={capabilities}
                refresh={refresh}
                connected={!connectionError}
              />
            ))
          ) : (
            <p className="text-muted">Loading evidence capabilities…</p>
          )}
        </section>
        <aside className="space-y-4 sticky top-6">
          <div className="rounded-xl border border-line bg-surface p-5">
            <ShieldCheck className="text-accent mb-3" />
            <h2 className="font-medium">Evidence and control</h2>
            <p className="text-sm text-muted mt-2 leading-relaxed">
              Add a document or information to one risk area, then reassess that
              module. Existing results stay available in history.
            </p>
            <p className="text-xs text-muted mt-4">
              Manual adjustments are recorded separately and require
              reconfirmation after an AI rerun.
            </p>
          </div>
          <div className="rounded-xl border border-line p-5 text-sm">
            <p className="text-muted text-xs">Invoice amount</p>
            <p className="num mt-1 font-semibold">
              {amount(invoice?.total, invoice?.currency)}
            </p>
            {invoice && (
              <a
                className="inline-block text-accent text-xs mt-3"
                href={backend.fileUrl(caseId, invoice.source_refs[0].source_id)}
              >
                Download original PDF
              </a>
            )}
            <p className="text-xs text-muted mt-4">
              AI: {capabilities?.model ?? "configured model"}
              <br />
              Policy: {capabilities?.policy_version}
              <br />
              Synthetic local reference data
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
