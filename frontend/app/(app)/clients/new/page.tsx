"use client";

import { useActionState } from "react";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type FormState = { error?: string } | null;

async function createClient(
  _prev: FormState,
  formData: FormData
): Promise<FormState> {
  const name = formData.get("name") as string;
  const website_url = formData.get("website_url") as string;

  if (!name.trim()) return { error: "Client name is required." };

  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/clients`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, website_url }),
      }
    );
    if (!res.ok) {
      const err = await res.json();
      return { error: err.detail || "Failed to create client." };
    }
    const client = await res.json();
    // Redirect via window location since router.push not available in action
    if (typeof window !== "undefined") {
      window.location.href = `/clients/${client.id}`;
    }
    return null;
  } catch {
    return { error: "Could not reach the server. Is the backend running?" };
  }
}

const inputClass = cn(
  "w-full bg-transparent border-0 border-b border-ink/20 font-mono text-sm text-ink",
  "py-3 focus:outline-none focus:border-ink transition-colors placeholder:text-graphite/50"
);

export default function NewClientPage() {
  const [state, action, isPending] = useActionState(createClient, null);

  return (
    <>
      {/* Back */}
      <Link
        href="/clients"
        className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors font-mono mb-10"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to Clients
      </Link>

      <header className="mb-10">
        <h1 className="font-display text-3xl font-bold text-ink mb-2">
          New Client
        </h1>
        <p className="text-sm text-graphite font-mono">
          After creating the client, run brand ingestion to build their voice profile.
        </p>
      </header>

      <form action={action} className="space-y-8">
        {state?.error && (
          <p className="text-sm font-mono text-danger border border-danger/20 bg-danger/5 px-4 py-3">
            {state.error}
          </p>
        )}

        <div className="space-y-6">
          <div>
            <label
              htmlFor="name"
              className="block text-xs font-mono text-graphite uppercase tracking-wider mb-2"
            >
              Client Name *
            </label>
            <input
              id="name"
              name="name"
              type="text"
              required
              disabled={isPending}
              placeholder="Acme Corp"
              className={inputClass}
            />
          </div>

          <div>
            <label
              htmlFor="website_url"
              className="block text-xs font-mono text-graphite uppercase tracking-wider mb-2"
            >
              Website URL
            </label>
            <input
              id="website_url"
              name="website_url"
              type="url"
              disabled={isPending}
              placeholder="https://example.com"
              className={inputClass}
            />
            <p className="text-xs text-graphite font-mono mt-2">
              Used during brand ingestion to extract tone and voice.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 pt-4 border-t border-border">
          <button
            type="submit"
            disabled={isPending}
            className={cn(
              "inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-8 py-3",
              "hover:bg-graphite transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Creating...
              </>
            ) : (
              "Create Client"
            )}
          </button>
          <Link
            href="/clients"
            className="text-sm text-graphite hover:text-ink transition-colors font-mono"
          >
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}
