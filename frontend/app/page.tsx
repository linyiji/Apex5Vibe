"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileSearch, ShieldCheck, UserCheck } from "lucide-react";
import InvoiceUploader from "@/components/InvoiceUploader";
import PastEvaluations from "@/components/PastEvaluations";
import StepIndicator from "@/components/StepIndicator";
import { extractInvoice, loadDemoInvoice } from "@/lib/api";
import { createCase } from "@/lib/case-store";
import { API_MODE } from "@/lib/runtime-config";
import UploadWorkspace from "@/components/live/UploadWorkspace";

const TRUST = [
  { icon: ShieldCheck, label: "Evidence-backed scoring" },
  { icon: FileSearch, label: "Explainable decisions" },
  { icon: UserCheck, label: "Human review supported" },
];

function MockUploadPage() {
  const router = useRouter();
  const [busy, setBusy] = useState<"upload" | "demo" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start(kind: "upload" | "demo", file?: File) {
    setBusy(kind);
    setError(null);
    try {
      const invoice = file ? await extractInvoice(file) : await loadDemoInvoice();
      router.push(`/assessment/${createCase(invoice, file)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong reading the invoice.");
      setBusy(null);
    }
  }

  return (
    <div className="max-w-2xl mx-auto pt-4">
      <StepIndicator current={1} />
      <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Assess an invoice</h1>
      <p className="mt-3 text-muted text-lg leading-relaxed">
        Upload an invoice to evaluate fraud risk, transaction authenticity, and financing eligibility.
      </p>

      <div className="mt-8">
        <InvoiceUploader busy={busy} onFile={(f) => start("upload", f)} onDemo={() => start("demo")} />
        {error && <p className="mt-3 text-sm text-risk" role="alert">{error}</p>}
      </div>

      <ul className="mt-12 grid sm:grid-cols-3 gap-4 text-sm text-muted">
        {TRUST.map(({ icon: Icon, label }) => (
          <li key={label} className="flex items-center gap-2">
            <Icon size={16} className="text-accent shrink-0" /> {label}
          </li>
        ))}
      </ul>

      <PastEvaluations />
    </div>
  );
}

export default function UploadPage() {
  return API_MODE === "live" ? <UploadWorkspace /> : <MockUploadPage />;
}
