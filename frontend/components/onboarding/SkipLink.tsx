"use client";

import type { ReactNode } from "react";

interface Props {
  onClick: () => void;
  children: ReactNode;
}

export function SkipLink({ onClick, children }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full text-center text-sm text-[#555555] mt-4 hover:text-[#111111] underline underline-offset-2"
    >
      {children}
    </button>
  );
}
