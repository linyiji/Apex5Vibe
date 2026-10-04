"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileUp, Loader2, RefreshCw } from "lucide-react";
import StepIndicator from "@/components/StepIndicator";
import { backend } from "@/lib/backend-api";
import {
  amount,
  validateFiles,
  type Capabilities,
  type Entity,
  type PartySelection,
  type QueuePage,
} from "@/lib/backend-types";
import PartyPicker, { button, control, primary } from "./PartyPicker";

export default function UploadWorkspace() {
  const router = useRouter();
  const invoiceInput = useRef<HTMLInputElement>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [buyer, setBuyer] = useState<PartySelection>({ mode: "skip" });
  const [seller, setSeller] = useState<PartySelection>({ mode: "skip" });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queue, setQueue] = useState<QueuePage | null>(null);
  const [band, setBand] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      backend.capabilities(controller.signal),
      backend.entities(controller.signal),
    ])
      .then(([cap, result]) => {
        setCapabilities(cap);
        setEntities(result.items);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    const controller = new AbortController();
    backend
      .queue(band, undefined, controller.signal)
      .then(setQueue)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [band, refresh]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!file || !capabilities) return;
    setError(null);
    setBusy(true);
    try {
      validateFiles([file], capabilities, true);
      for (const [side, party] of [
        ["buyer", buyer],
        ["seller", seller],
      ] as const) {
        if (party.mode === "manual" && !party.legal_name.trim())
          throw new Error(`Enter the ${side} company name.`);
        if (party.mode === "existing" && !party.entity_id)
          throw new Error(`Select an existing ${side} company.`);
      }
      const created = await backend.create(buyer, seller);
      await backend.uploadInvoice(created.case_id, created.case_revision, file);
      router.push(`/assessment/${encodeURIComponent(created.case_id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
      setBusy(false);
    }
  }

  async function loadMore() {
    if (!queue?.next_cursor) return;
    try {
      const next = await backend.queue(band, queue.next_cursor);
      setQueue({
        items: [...queue.items, ...next.items],
        next_cursor: next.next_cursor,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the queue.");
    }
  }

  return (
    <div>
      <StepIndicator current={1} />
      <div className="max-w-3xl mx-auto">
        <p className="text-xs tracking-widest uppercase text-accent">
          Assessment workspace
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">
          Assess an invoice
        </h1>
        <p className="mt-3 text-muted">
          Upload a commercial invoice. Review its details, then assess seven
          risk modules with supporting evidence.
        </p>
        <form noValidate onSubmit={submit} className="mt-7 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <PartyPicker
              side="Seller"
              value={seller}
              onChange={setSeller}
              entities={entities}
              disabled={busy}
            />
            <PartyPicker
              side="Buyer"
              value={buyer}
              onChange={setBuyer}
              entities={entities}
              disabled={busy}
            />
          </div>
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!busy) setFile(e.dataTransfer.files[0] ?? null);
            }}
            className="rounded-2xl border border-dashed border-line-strong bg-surface p-7"
          >
            <FileUp className="text-accent mb-3" size={28} />
            <label htmlFor="invoice-file" className="block font-medium">
              Choose an invoice PDF
            </label>
            <p className="mt-1 text-sm text-muted">
              Commercial invoice form · PDF · up to{" "}
              {capabilities ? capabilities.max_file_bytes / 1024 / 1024 : 20}{" "}
              MiB
            </p>
            <p className="mt-1 text-xs text-faint">
              Use the supplied Case 1 or Case 2 PDF for this local
              demonstration. Scanned invoices are not supported.
            </p>
            <input
              id="invoice-file"
              ref={invoiceInput}
              type="file"
              accept=".pdf"
              disabled={busy || !capabilities}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="hidden"
            />
            <button
              type="button"
              className={`${button} mt-4`}
              disabled={busy || !capabilities}
              onClick={() => invoiceInput.current?.click()}
            >
              Choose PDF
            </button>
            {!file && (
              <span className="text-xs text-muted ml-3">No file selected</span>
            )}
            {file && (
              <p className="mt-3 text-sm text-accent">Selected: {file.name}</p>
            )}
          </div>
          {error && (
            <p
              className="rounded-lg border border-risk/30 p-3 text-risk text-sm"
              role="alert"
            >
              {error}
            </p>
          )}
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted">
              {capabilities
                ? `Live AI · ${capabilities.model ?? "configured model"} · synthetic reference data`
                : "Connecting to assessment service…"}
            </span>
            <button
              type="submit"
              disabled={busy || !file || !capabilities}
              className={`${primary} flex items-center gap-2`}
            >
              {busy && <Loader2 size={16} className="animate-spin" />}
              {busy ? "Uploading…" : "Upload Invoice"}
            </button>
          </div>
        </form>
      </div>
      <section
        className="mt-14 border-t border-line pt-6"
        aria-label="Assessment queue"
      >
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-xl font-semibold">Assessment queue</h2>
            <p className="text-sm text-muted">
              Saved cases and current assessment status.
            </p>
          </div>
          <div className="flex gap-3">
            <select
              aria-label="Filter risk"
              className={control}
              value={band}
              onChange={(e) => setBand(e.target.value)}
            >
              <option value="">All risks</option>
              <option value="LOW">Low</option>
              <option value="HIGH">High</option>
            </select>
            <button
              className={button}
              type="button"
              aria-label="Refresh queue"
              onClick={() => {
                setError(null);
                setRefresh((x) => x + 1);
              }}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
        <div className="rounded-xl border border-line overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface text-muted">
              <tr>
                {[
                  "Invoice",
                  "Amount",
                  "Risk",
                  "Assessment",
                  "Financing",
                  "",
                ].map((s, i) => (
                  <th className="p-4 font-medium" key={i}>
                    {s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {queue?.items.map((item) => (
                <tr key={item.case_id} className="border-t border-line">
                  <td className="p-4 font-medium">
                    {item.invoice_number ?? "New invoice"}
                  </td>
                  <td className="p-4 num">
                    {amount(item.amount, item.currency ?? "GBP")}
                  </td>
                  <td
                    className={`p-4 ${item.risk_band === "HIGH" ? "text-risk" : item.risk_band === "LOW" ? "text-ok" : "text-muted"}`}
                  >
                    {item.risk_band ?? "Pending"}
                    {item.risk_band && !item.risk_is_current && (
                      <span className="text-xs text-warn block">
                        Previous result
                      </span>
                    )}
                  </td>
                  <td className="p-4 capitalize">
                    {item.aggregate_status === "unavailable"
                      ? item.stage
                      : item.aggregate_status}
                  </td>
                  <td className="p-4 capitalize">
                    {item.decision_status.replaceAll("_", " ")}
                  </td>
                  <td className="p-4 text-right">
                    <Link
                      className="text-accent hover:underline"
                      href={`/assessment/${item.case_id}`}
                    >
                      Open case
                    </Link>
                  </td>
                </tr>
              ))}
              {queue?.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted">
                    No matching cases. Upload an invoice to begin.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {queue?.next_cursor && (
          <button className={`${button} mt-4`} onClick={loadMore}>
            Load more cases
          </button>
        )}
      </section>
    </div>
  );
}
