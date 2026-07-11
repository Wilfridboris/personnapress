interface Props {
  step: number;
  total: number;
}

export function ProgressIndicator({ step, total }: Props) {
  return (
    <p className="text-xs font-medium uppercase tracking-[0.06em] text-[#555555] mb-6">
      {step} of {total}
    </p>
  );
}
