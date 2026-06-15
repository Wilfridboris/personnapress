"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const RESEND_COOLDOWN_MS = 60_000;

export function VerifyEmailClient({ email: initialEmail }: { email?: string }) {
  const [email, setEmail] = useState(initialEmail ?? "");
  const [status, setStatus] = useState<"idle" | "sent" | "cooldown">("idle");
  const [lastSent, setLastSent] = useState(0);

  async function handleResend(e?: React.FormEvent) {
    e?.preventDefault();
    if (!email) return;
    const now = Date.now();
    if (now - lastSent < RESEND_COOLDOWN_MS) {
      setStatus("cooldown");
      return;
    }

    try {
      await fetch(`${API_BASE}/api/v1/auth/resend-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setLastSent(now);
      setStatus("sent");
    } catch {
      setStatus("sent");
    }
  }

  return (
    <div>
      {status === "sent" && (
        <p className="text-sm text-success mb-4" role="status">
          Verification email sent.
        </p>
      )}
      {status === "cooldown" && (
        <p className="text-sm text-graphite mb-4" role="status">
          Please wait a moment before requesting another email.
        </p>
      )}
      {initialEmail ? (
        <Button
          type="button"
          variant="secondary"
          onClick={() => handleResend()}
          disabled={status === "cooldown"}
        >
          Resend verification email
        </Button>
      ) : (
        <form onSubmit={handleResend} className="flex flex-col gap-3">
          <label htmlFor="resend-email" className="block text-sm text-ink text-left">
            Email address
          </label>
          <Input
            id="resend-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Button
            type="submit"
            variant="secondary"
            disabled={status === "cooldown" || !email}
          >
            Resend verification email
          </Button>
        </form>
      )}
    </div>
  );
}
