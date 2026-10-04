const STEPS = ["Upload", "Review", "Assessment", "Decision"];

/** Subtle progress line: current step highlighted, earlier steps dimmed with a check. */
export default function StepIndicator({ current }: { current: 1 | 2 | 3 | 4 }) {
  return (
    <ol className="flex items-center gap-2 text-xs text-faint mb-8" aria-label="Progress">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const state = n < current ? "done" : n === current ? "current" : "todo";
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={
                state === "current" ? "text-accent font-medium" : state === "done" ? "text-muted" : ""
              }
              aria-current={state === "current" ? "step" : undefined}
            >
              {state === "done" ? "✓ " : `${n}. `}
              {label}
            </span>
            {n < STEPS.length && <span className="w-6 h-px bg-line" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
