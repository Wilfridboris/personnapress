"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

const ALLOWED_REDIRECT_PATHS = new Set(["/onboarding", "/dashboard"]);

function safeRedirectPath(path: string | undefined | null): string {
  if (path && ALLOWED_REDIRECT_PATHS.has(path)) return path;
  return "/onboarding";
}

export function VerifyEmailConfirmClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Missing verification token.");
      return;
    }

    async function verify() {
      try {
        const res = await fetch(
          `/api/auth/verify-email?token=${encodeURIComponent(token!)}`,
        );
        const data = await res.json();
        if (!res.ok) {
          setError(data?.detail?.error?.message ?? "Verification failed.");
          return;
        }
        router.replace(safeRedirectPath(data.redirect_url));
      } catch {
        setError("Unable to reach the server. Please try again.");
      }
    }

    verify();
  }, [token, router]);

  if (error) {
    return (
      <div className="w-full max-w-sm text-center">
        <h1 className="font-display text-2xl font-bold text-ink mb-4">Verification failed</h1>
        <p className="text-sm text-danger mb-6" role="alert">
          {error}
        </p>
        <Link href="/verify-email" className="text-sm text-ink underline underline-offset-2">
          Request a new verification link
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full max-w-sm text-center">
      <p className="text-sm text-graphite">Verifying your email...</p>
    </div>
  );
}
