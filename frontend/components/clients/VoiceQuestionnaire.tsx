"use client";

import { useState } from "react";
import { clientsApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { BrainDumpInput, Input } from "@/components/ui/Input";

interface Props {
  clientId: string;
  onJobStarted: (jobId: string) => void;
}

type Step = 1 | 2 | 3;

interface SliderValues {
  formal_casual: number;
  professional_friendly: number;
  concise_elaborate: number;
}

// ── Section label ──────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-sans text-xs uppercase tracking-[0.06em] text-[#111111] mb-3">
      {children}
    </p>
  );
}

// ── Single tone slider pair ────────────────────────────────────────────────────
interface SliderPairProps {
  leftLabel: string;
  rightLabel: string;
  value: number;
  onChange: (v: number) => void;
}

function SliderPair({ leftLabel, rightLabel, value, onChange }: SliderPairProps) {
  return (
    <div className="mb-6">
      <div className="flex justify-between mb-1">
        <span className="text-xs text-[#555555] font-sans">{leftLabel}</span>
        <span className="text-xs text-[#555555] font-sans">{rightLabel}</span>
      </div>
      <input
        type="range"
        min={1}
        max={5}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#111111]"
        aria-label={`${leftLabel} to ${rightLabel} tone — currently ${value}`}
        aria-valuenow={value}
        aria-valuemin={1}
        aria-valuemax={5}
        aria-valuetext={`${value} of 5`}
      />
      <div className="flex justify-between mt-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <span
            key={n}
            className={`text-xs font-mono ${n === value ? "text-[#111111] font-bold" : "text-[#555555]"}`}
          >
            {n}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Step 1: Tone sliders ───────────────────────────────────────────────────────
interface Step1Props {
  sliders: SliderValues;
  onChange: (k: keyof SliderValues, v: number) => void;
}

function Step1({ sliders, onChange }: Step1Props) {
  return (
    <div>
      <SectionLabel>Tone style</SectionLabel>
      <SliderPair
        leftLabel="Formal"
        rightLabel="Casual"
        value={sliders.formal_casual}
        onChange={(v) => onChange("formal_casual", v)}
      />
      <SliderPair
        leftLabel="Professional"
        rightLabel="Friendly"
        value={sliders.professional_friendly}
        onChange={(v) => onChange("professional_friendly", v)}
      />
      <SliderPair
        leftLabel="Concise"
        rightLabel="Elaborate"
        value={sliders.concise_elaborate}
        onChange={(v) => onChange("concise_elaborate", v)}
      />
    </div>
  );
}

// ── Step 2: Sample texts ───────────────────────────────────────────────────────
interface Step2Props {
  samples: string[];
  onChange: (index: number, value: string) => void;
}

function Step2({ samples, onChange }: Step2Props) {
  return (
    <div>
      <SectionLabel>Sample writing</SectionLabel>
      <p className="text-sm text-[#555555] mb-4">
        All three fields are optional. Leave blank if you prefer.
      </p>
      {[0, 1, 2].map((i) => (
        <div key={i} className="mb-6">
          <label
            htmlFor={`sample-${i}`}
            className="block text-xs uppercase tracking-[0.06em] text-[#555555] mb-1"
          >
            Paste a piece of writing that sounds like you.
          </label>
          <BrainDumpInput
            id={`sample-${i}`}
            value={samples[i] ?? ""}
            onChange={(e) => onChange(i, e.target.value)}
            placeholder="Paste writing here…"
            className="min-h-[100px]"
          />
        </div>
      ))}
    </div>
  );
}

// ── Step 3: Reference writers ──────────────────────────────────────────────────
interface Step3Props {
  urls: string[];
  onChange: (index: number, value: string) => void;
  onSkip: () => void;
}

function Step3({ urls, onChange, onSkip }: Step3Props) {
  return (
    <div>
      <SectionLabel>Reference writers</SectionLabel>
      <p className="text-sm text-[#555555] mb-4">Optional.</p>
      {[0, 1, 2].map((i) => (
        <div key={i} className="mb-4">
          <label
            htmlFor={`ref-url-${i}`}
            className="block text-xs uppercase tracking-[0.06em] text-[#555555] mb-1"
          >
            A writer whose style you admire.
          </label>
          <Input
            id={`ref-url-${i}`}
            type="url"
            value={urls[i] ?? ""}
            onChange={(e) => onChange(i, e.target.value)}
            placeholder="https://example.com/author"
          />
        </div>
      ))}
      <button
        type="button"
        onClick={onSkip}
        className="text-sm text-[#555555] underline underline-offset-2 hover:text-[#111111] mt-2"
      >
        Skip this step
      </button>
    </div>
  );
}

// ── Main wizard component ──────────────────────────────────────────────────────
export function VoiceQuestionnaire({ clientId, onJobStarted }: Props) {
  const [step, setStep] = useState<Step>(1);
  const [sliders, setSliders] = useState<SliderValues>({
    formal_casual: 3,
    professional_friendly: 3,
    concise_elaborate: 3,
  });
  const [samples, setSamples] = useState<string[]>(["", "", ""]);
  const [refUrls, setRefUrls] = useState<string[]>(["", "", ""]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateSlider = (k: keyof SliderValues, v: number) =>
    setSliders((prev) => ({ ...prev, [k]: v }));

  const updateSample = (i: number, v: string) =>
    setSamples((prev) => {
      const next = [...prev];
      next[i] = v;
      return next;
    });

  const updateRefUrl = (i: number, v: string) =>
    setRefUrls((prev) => {
      const next = [...prev];
      next[i] = v;
      return next;
    });

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await clientsApi.submitQuestionnaire(clientId, {
        tone_sliders: sliders,
        sample_texts: samples.filter(Boolean),
        reference_urls: refUrls.filter(Boolean),
      });
      onJobStarted(result.job_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed. Please try again.");
      setSubmitting(false);
    }
  };

  const handleSkipStep3 = () => handleSubmit();

  return (
    <div className="max-w-md">
      {/* Progress indicator */}
      <p className="font-sans text-xs uppercase tracking-[0.06em] text-[#555555] mb-8">
        Step {step} of 3
      </p>

      {step === 1 && (
        <Step1 sliders={sliders} onChange={updateSlider} />
      )}
      {step === 2 && (
        <Step2 samples={samples} onChange={updateSample} />
      )}
      {step === 3 && (
        <Step3 urls={refUrls} onChange={updateRefUrl} onSkip={handleSkipStep3} />
      )}

      {error && (
        <p role="alert" className="text-sm text-[#8B0000] mb-4">
          {error}
        </p>
      )}

      {/* Navigation buttons */}
      <div className="flex items-center gap-3 mt-8">
        {step > 1 && (
          <Button
            variant="secondary"
            onClick={() => setStep((s) => (s - 1) as Step)}
            disabled={submitting}
            type="button"
          >
            Back
          </Button>
        )}

        {step < 3 && (
          <Button
            onClick={() => setStep((s) => (s + 1) as Step)}
            type="button"
          >
            Next
          </Button>
        )}

        {step === 3 && (
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            aria-busy={submitting}
            type="button"
          >
            {submitting ? "Submitting..." : "Submit questionnaire"}
          </Button>
        )}
      </div>
    </div>
  );
}
