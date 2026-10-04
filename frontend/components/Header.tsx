import Link from "next/link";
import { Plus } from "lucide-react";
import { API_MODE } from "@/lib/runtime-config";

export default function Header() {
  return (
    <header className="border-b border-line">
      <div className="max-w-7xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-2 to-accent" aria-hidden />
          <span>
            <span className="block font-semibold tracking-tight leading-tight">Apex5Vibe</span>
            <span className="block text-xs text-muted leading-tight">AI-powered invoice financing assessment</span>
          </span>
        </Link>
        <div className="flex items-center gap-3">
          {API_MODE === "live" && <span className="text-xs text-accent border border-accent/30 rounded-full px-3 py-1">Live AI assessment</span>}
          {API_MODE === "mock" && (
            <span
              className="hidden sm:inline text-xs text-warn border border-warn/30 rounded-full px-3 py-1"
              title="The scoring engine and AI Risk Analyst are simulated in the browser until the backend is connected."
            >
              Demo · simulated engine
            </span>
          )}
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text border border-line rounded-lg px-3 py-1.5"
          >
            <Plus size={14} /> New assessment
          </Link>
        </div>
      </div>
    </header>
  );
}
