"use client";

import { useRef, useState } from "react";
import { FileText, Loader2, Upload } from "lucide-react";

const MAX_MB = 15;
const OK_EXT = /\.(pdf|png|jpe?g|webp)$/i;
const OK_TYPES = ["application/pdf", "image/png", "image/jpeg", "image/webp"];

interface Props {
  busy: "upload" | "demo" | null;
  onFile: (file: File) => void;
  onDemo: () => void;
}

export default function InvoiceUploader({ busy, onFile, onDemo }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function accept(file: File | undefined) {
    if (!file) return;
    setError(null);
    // Checked here too because drag-and-drop ignores the input's accept= filter.
    if (!OK_TYPES.includes(file.type) && !OK_EXT.test(file.name)) {
      setError(/\.(heic|heif)$/i.test(file.name)
        ? "iPhone HEIC photos aren't supported. Export the photo as JPEG and try again."
        : "Unsupported file. Upload a PDF, PNG or JPG.");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File is ${(file.size / 1e6).toFixed(1)} MB. The limit is ${MAX_MB} MB.`);
      return;
    }
    onFile(file);
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => !busy && input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !busy && input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); if (!busy) accept(e.dataTransfer.files[0]); }}
        className={`rounded-2xl border border-dashed px-6 py-14 text-center cursor-pointer transition-colors ${
          drag ? "border-accent bg-accent/5" : "border-line-strong hover:border-accent/60 bg-surface"
        }`}
      >
        <div className="mx-auto mb-4 w-12 h-12 rounded-xl grid place-items-center bg-surface-2 border border-line text-accent">
          {busy === "upload" ? <Loader2 className="animate-spin" size={22} /> : <FileText size={22} />}
        </div>
        <p className="text-lg font-medium">{busy === "upload" ? "Reading invoice…" : "Drop invoice here"}</p>
        <p className="text-sm text-muted mt-1">PDF, PNG or JPG · max {MAX_MB} MB</p>
        <input
          ref={input}
          type="file"
          className="hidden"
          accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp"
          onChange={(e) => { accept(e.target.files?.[0]); e.target.value = ""; }}
        />
      </div>

      {error && <p className="mt-3 text-sm text-risk" role="alert">{error}</p>}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={!!busy}
          onClick={() => input.current?.click()}
          className="inline-flex items-center gap-2 rounded-lg bg-accent text-bg font-semibold px-5 py-2.5 hover:brightness-110 disabled:opacity-50"
        >
          <Upload size={16} /> Upload Invoice
        </button>
        <button
          type="button"
          disabled={!!busy}
          onClick={onDemo}
          className="inline-flex items-center gap-2 rounded-lg border border-line-strong px-5 py-2.5 text-text hover:bg-surface-2 disabled:opacity-50"
        >
          {busy === "demo" && <Loader2 className="animate-spin" size={16} />} Use Demo Invoice
        </button>
      </div>
    </div>
  );
}
