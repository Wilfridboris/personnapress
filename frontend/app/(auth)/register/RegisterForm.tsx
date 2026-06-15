"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function RegisterForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  function validatePassword(value: string): boolean {
    if (value.length > 0 && value.length < 8) {
      setPasswordError("Minimum 8 characters");
      return false;
    }
    setPasswordError("");
    return true;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");

    if (password.length < 8) {
      setPasswordError("Minimum 8 characters");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setFormError(data?.detail?.error?.message ?? "Something went wrong.");
        return;
      }

      setSuccess(true);
    } catch {
      setFormError("Unable to reach the server. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleSignUp() {
    window.location.href = "/api/auth/google/initiate";
  }

  if (success) {
    return (
      <p className="text-sm text-ink text-center" role="status">
        Check your email to verify your account.
      </p>
    );
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
          autoComplete="new-password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            validatePassword(e.target.value);
          }}
          required
          aria-describedby={passwordError ? "password-error" : "password-hint"}
        />
        {passwordError ? (
          <p id="password-error" role="alert" className="text-xs text-danger mt-1">
            {passwordError}
          </p>
        ) : (
          <p id="password-hint" className="text-xs text-graphite mt-1">
            Minimum 8 characters
          </p>
        )}
      </div>

      {formError && (
        <p id="form-error" role="alert" className="text-sm text-danger mt-2 mb-4">
          {formError}
        </p>
      )}

      <Button type="submit" variant="primary" className="w-full mb-4" disabled={loading}>
        {loading ? "Creating account..." : "Create account"}
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
        onClick={handleGoogleSignUp}
        aria-label="Sign up with Google"
      >
        Sign up with Google
      </Button>

      <p className="text-sm text-graphite text-center">
        Already have an account?{" "}
        <Link href="/login" className="text-ink underline underline-offset-2 hover:no-underline">
          Log in.
        </Link>
      </p>
    </form>
  );
}
