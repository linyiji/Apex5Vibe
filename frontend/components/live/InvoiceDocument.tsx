"use client";

import { useEffect, useState } from "react";
import { backend } from "@/lib/backend-api";

export default function InvoiceDocument({
  caseId,
  fileId,
}: {
  caseId: string;
  fileId: string;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;
    fetch(backend.fileUrl(caseId, fileId), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Preview unavailable");
        return response.blob();
      })
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
        setFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [caseId, fileId]);
  return (
    <div className="rounded-xl border border-line bg-surface overflow-hidden">
      <div className="p-3 text-sm flex justify-between">
        <span>Original invoice</span>
        <a
          className="text-accent hover:underline"
          href={backend.fileUrl(caseId, fileId)}
        >
          Download PDF
        </a>
      </div>
      {url ? (
        <iframe
          title="Original invoice PDF"
          src={url}
          className="w-full h-[570px] bg-white"
        />
      ) : (
        <div className="h-72 grid place-items-center text-muted">
          {failed
            ? "Preview unavailable. Download the PDF above."
            : "Loading invoice…"}
        </div>
      )}
    </div>
  );
}
