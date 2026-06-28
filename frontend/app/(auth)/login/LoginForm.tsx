"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { fetchAPI, APIError } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [errorCode, setErrorCode] = useState("");
  const [verificationEmail, setVerificationEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendStatus, setResendStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    setErrorCode("");
    setResendStatus("idle");
    setLoading(true);

    try {
      await fetchAPI("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      router.refresh();
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      const code = err instanceof APIError ? err.code : "";

      if (code === "EMAIL_NOT_VERIFIED") {
        setErrorCode("EMAIL_NOT_VERIFIED");
        setFormError(message);
        setVerificationEmail(email);
      } else {
        setFormError(message || "Invalid email or password.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleResendVerification() {
    setResendStatus("sending");
    try {
      await fetchAPI("/auth/resend-verification", {
        method: "POST",
        body: JSON.stringify({ email: verificationEmail }),
      });
      setResendStatus("sent");
    } catch {
      setResendStatus("error");
    }
  }

  function handleGoogleSignIn() {
    window.location.href = "/api/auth/google/initiate";
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="mb-5">
        <label htmlFor="email" className="block text-sm text-ink mb-1">
          Email address
        </label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          aria-describedby={formError ? "form-error" : undefined}
        />
      </div>

      <div className="mb-6">
        <label htmlFor="password" className="block text-sm text-ink mb-1">
          Password
        </label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          aria-describedby={formError ? "form-error" : undefined}
        />
      </div>

      {formError && (
        <div id="form-error" role="alert" className="text-sm text-danger mt-2 mb-4">
          <p>{formError}</p>
          {errorCode === "EMAIL_NOT_VERIFIED" && (
            <>
              <button
                type="button"
                onClick={handleResendVerification}
                disabled={resendStatus === "sending" || resendStatus === "sent"}
                className="underline underline-offset-2 hover:no-underline mt-1 text-left disabled:opacity-50"
              >
                {resendStatus === "sending"
                  ? "Sending..."
                  : resendStatus === "sent"
                  ? "Email sent!"
                  : "Resend verification email"}
              </button>
              {resendStatus === "error" && (
                <span className="block text-xs mt-1">Failed to resend. Please try again.</span>
              )}
            </>
          )}
        </div>
      )}

      <Button type="submit" variant="primary" className="w-full mb-4" disabled={loading}>
        {loading ? "Logging in..." : "Log in"}
      </Button>

      <div className="flex items-center gap-3 mb-4">
        <span className="flex-1 h-px bg-border" aria-hidden="true" />
        <span className="text-xs text-graphite">or</span>
        <span className="flex-1 h-px bg-border" aria-hidden="true" />
      </div>

      <Button
        type="button"
        variant="secondary"
        className="w-full mb-6"
        onClick={handleGoogleSignIn}
        aria-label="Sign in with Google"
      >
        Sign in with Google
      </Button>

      <p className="text-sm text-graphite text-center">
        No account?{" "}
        <Link href="/register" className="text-ink underline underline-offset-2 hover:no-underline">
          Create one.
        </Link>
      </p>
    </form>
  );
}
