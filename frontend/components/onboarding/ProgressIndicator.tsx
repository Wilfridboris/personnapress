import { Check } from "lucide-react";

const STEP_LABELS = [
  "Create client",
  "Voice setup",
  "Write content",
  "Publish",
] as const;

interface Props {
  step: number;
  total?: number;
}

export function ProgressIndicator({ step }: Props) {
  return (
    <nav aria-label="Onboarding progress" className="mb-6">
      <ol className="flex items-center gap-0">
        {STEP_LABELS.map((label, i) => {
          const stepNum = i + 1;
          const isCompleted = stepNum < step;
          const isCurrent = stepNum === step;

          return (
            <li
              key={label}
              aria-current={isCurrent ? "step" : undefined}
              className="flex items-center"
            >
              <span className="flex items-center gap-1.5">
                <span
                  className={
                    isCurrent
                      ? "text-xs font-medium uppercase tracking-[0.06em] text-[#111111]"
                      : isCompleted
                      ? "text-xs font-medium uppercase tracking-[0.06em] text-[#555555]"
                      : "text-xs uppercase tracking-[0.06em] text-[#AAAAAA]"
                  }
                >
                  {isCompleted && (
                    <>
                      <Check size={10} aria-hidden="true" className="inline mr-0.5" />
                      <span className="sr-only">completed: </span>
                    </>
                  )}
                  {label}
                </span>
              </span>
              {stepNum < STEP_LABELS.length && (
                <span aria-hidden="true" className="mx-2 text-[#DDDDDD] text-xs select-none">
                  /
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
