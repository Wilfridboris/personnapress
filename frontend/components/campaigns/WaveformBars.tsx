"use client";

import { useEffect, useRef } from "react";

interface WaveformBarsProps {
  analyserNode: AnalyserNode | null;
}

const NUM_BARS = 6;
const MIN_H = 3;
const MAX_H = 20;
// Voice-range frequency bin indices from a 32-bin (fftSize=64) analyser
const BIN_INDICES = [2, 5, 9, 13, 17, 21] as const;

export function WaveformBars({ analyserNode }: WaveformBarsProps) {
  const barsRef = useRef<(HTMLSpanElement | null)[]>([]);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!analyserNode) return;

    const dataArray = new Uint8Array(analyserNode.frequencyBinCount);

    function tick() {
      analyserNode!.getByteFrequencyData(dataArray);
      barsRef.current.forEach((bar, i) => {
        if (!bar) return;
        const value = dataArray[BIN_INDICES[i]] ?? 0;
        bar.style.height = `${MIN_H + (value / 255) * (MAX_H - MIN_H)}px`;
      });
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [analyserNode]);

  return (
    <span
      data-testid="voice-waveform"
      aria-hidden="true"
      className="inline-flex items-end gap-[2px] h-5"
    >
      {Array.from({ length: NUM_BARS }, (_, i) => (
        <span
          key={i}
          ref={(el) => {
            barsRef.current[i] = el;
          }}
          className="w-[3px] bg-ink transition-[height] duration-75 ease-out motion-reduce:transition-none"
          style={{ height: `${MIN_H}px` }}
        />
      ))}
    </span>
  );
}
