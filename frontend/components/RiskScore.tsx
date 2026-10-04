"use client";

import { useEffect, useRef, useState } from "react";
import { BAND_LABEL, BAND_TEXT } from "@/lib/format";
import type { RiskBand } from "@/lib/types";

/** Big score number; counts from the previous score to the new one after a reassessment. */
export default function RiskScore({ score, band, from }: { score: number; band: RiskBand; from?: number }) {
  const [shown, setShown] = useState(from ?? score);
  const start = useRef(from ?? score);

  useEffect(() => {
    const begin = start.current;
    if (begin === score) return;
    const t0 = performance.now();
    const duration = 900;
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(Math.round(begin + (score - begin) * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
      else start.current = score;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  return (
    <div>
      <div className="flex items-baseline gap-1">
        <span className={`text-5xl font-semibold num tracking-tight ${BAND_TEXT[band]}`}>{shown}</span>
        <span className="text-muted text-lg">/ 100</span>
      </div>
      <div className={`mt-1 text-sm font-medium ${BAND_TEXT[band]}`}>{BAND_LABEL[band]}</div>
    </div>
  );
}
