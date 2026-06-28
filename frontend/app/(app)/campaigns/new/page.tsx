"use client";

import { useActionState, useEffect, useState } from "react";
import { ArrowLeft, Loader2, Cpu } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type FormState = { error?: string; campaignId?: string } | null;

async function submitBrainDump(
  _prev: FormState,
  formData: FormData
): Promise<FormState> {
  const client_id = formData.get("client_id") as string;
  const brain_dump = formData.get("brain_dump") as string;

  if (!client_id) return { error: "Please select a client." };
  if (!brain_dump.trim() || brain_dump.trim().length < 20) {
    return { error: "Brain dump is too short. Give the agent something to work with." };
  }

  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/campaigns`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id,
          brain_dump: brain_dump.trim(),
        }),
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { error: err.error?.message || err.detail || "Failed to start campaign generation." };
    }
    const data = await res.json();
    return { campaignId: data.campaign_id };
  } catch {
    return { error: "Could not reach the server. Is the backend running?" };
  }
}

export default function NewCampaignPage() {
  const [state, action, isPending] = useActionState(submitBrainDump, null);
  const [clients, setClients] = useState<{ id: string; name: string }[]>([]);
  const [clientsError, setClientsError] = useState(false);
  const [charCount, setCharCount] = useState(0);

  useEffect(() => {
    fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/clients`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then(setClients)
      .catch(() => setClientsError(true));
  }, []);

  useEffect(() => {
    if (state?.campaignId) {
      window.location.href = `/campaigns/${state.campaignId}`;
    }
  }, [state]);

  const inputClass = cn(
    "w-full bg-transparent border-0 border-b border-ink/20 font-mono text-sm text-ink",
    "py-3 focus:outline-none focus:border-ink transition-colors placeholder:text-graphite/50"
  );

  return (
    <>
      {/* Back */}
      <Link
        href="/campaigns"
        className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors font-mono mb-10"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to Campaigns
      </Link>

      <header className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <Cpu className="size-5 text-graphite" aria-hidden="true" />
          <p className="font-mono text-xs text-graphite uppercase tracking-widest">
            New Campaign
          </p>
        </div>
        <h1 className="font-display text-3xl font-bold text-ink mb-2">
          Brain Dump
        </h1>
        <p className="text-sm text-graphite font-mono">
          Drop your raw idea. No structure needed. The agent handles the rest.
        </p>
      </header>

      <form action={action} className="space-y-8">
        {state?.error && (
          <p className="text-sm font-mono text-danger border border-danger/20 bg-danger/5 px-4 py-3">
            {state.error}
          </p>
        )}

        {/* Client selector */}
        <div>
          <label
            htmlFor="client_id"
            className="block text-xs font-mono text-graphite uppercase tracking-wider mb-2"
          >
            Client *
          </label>
          <select
            id="client_id"
            name="client_id"
            required
            disabled={isPending}
            className={cn(
              inputClass,
              "cursor-pointer appearance-none"
            )}
          >
            <option value="">Select a client...</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {clientsError ? (
            <p className="text-xs text-danger font-mono mt-2">
              Could not load clients. Is the backend running?
            </p>
          ) : clients.length === 0 ? (
            <p className="text-xs text-graphite font-mono mt-2">
              No clients yet.{" "}
              <Link href="/clients/new" className="underline hover:text-ink">
                Create one first.
              </Link>
            </p>
          ) : null}
        </div>

        {/* Brain dump textarea */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="brain_dump"
              className="block text-xs font-mono text-graphite uppercase tracking-wider"
            >
              Your Brain Dump *
            </label>
            <span className="text-xs font-mono text-graphite">
              {charCount} chars
            </span>
          </div>
          <textarea
            id="brain_dump"
            name="brain_dump"
            required
            disabled={isPending}
            rows={16}
            onChange={(e) => setCharCount(e.target.value.length)}
            placeholder={`Paste anything here:
- Voice note transcript
- Rough bullet points
- A few sentences of a raw idea
- A half-finished tweet thread

No structure needed. The agent reads your brand voice profile and writes the full SEO blog post + social posts from whatever you give it.`}
            className={cn(
              "w-full bg-transparent border border-ink/10 font-mono text-sm text-ink",
              "p-4 focus:outline-none focus:border-ink transition-colors resize-none",
              "placeholder:text-graphite/40 leading-relaxed"
            )}
          />
        </div>

        {/* Submit */}
        <div className="flex items-center gap-4 pt-2 border-t border-border">
          <button
            type="submit"
            disabled={isPending || clients.length === 0}
            className={cn(
              "inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-8 py-3",
              "hover:bg-graphite transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Generating draft...
              </>
            ) : (
              <>
                <Cpu className="size-4" aria-hidden="true" />
                Generate Campaign
              </>
            )}
          </button>
          {isPending && (
            <p className="text-xs text-graphite font-mono">
              Writing blog post, social posts, and featured image. This takes 30-90 seconds.
            </p>
          )}
        </div>
      </form>
    </>
  );
}
