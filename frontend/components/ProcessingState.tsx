"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

export const ASSESSMENT_STEPS = [
  "Validating invoice integrity",
  "Verifying buyer",
  "Verifying seller and bank account",
  "Checking transaction plausibility",
  "Analysing buyer–seller relationship",
  "Reviewing payment behaviour",
  "Searching for duplicate financing",
  "Applying financing policy",
];

export const REASSESS_STEPS = [
  "Updating evidence",
  "Recalculating affected modules",
  "Updating risk score",
  "Generating revised recommendation",
];

interface Props {
  title: string;
  steps: string[];
  /** ms per step; the parent waits for `onDone` before showing results. */
  stepMs?: number;
  onDone: () => void;
}

/** Ticks through the steps, then calls onDone. The real API call runs in parallel. */
export default function ProcessingState({ title, steps, stepMs = 380, onDone }: Props) {
  const [done, setDone] = useState(0);

  useEffect(() => {
    if (done >= steps.length) {
      const t = setTimeout(onDone, 250);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setDone((d) => d + 1), stepMs);
    return () => clearTimeout(t);
  }, [done, steps.length, stepMs, onDone]);

  return (
    <div className="max-w-md mx-auto py-10 fade-up" role="status" aria-live="polite">
      <h2 className="text-xl font-semibold mb-6">{title}</h2>
      <ul className="space-y-3">
        {steps.map((s, i) => (
          <li key={s} className={`flex items-center gap-3 text-sm ${i < done ? "text-text" : i === done ? "text-accent" : "text-faint"}`}>
            <span className="w-5 h-5 grid place-items-center">
              {i < done ? <Check size={16} className="text-ok" /> : i === done ? <Loader2 size={15} className="animate-spin" /> : <span className="w-1.5 h-1.5 rounded-full bg-line-strong" />}
            </span>
            {s}
          </li>
        ))}
      </ul>
    </div>
  );
}
