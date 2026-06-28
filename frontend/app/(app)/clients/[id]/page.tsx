import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { IngestButton } from "./ingest-button";

type Props = { params: Promise<{ id: string }> };

async function getClient(id: string) {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/clients/${id}`,
      { cache: "no-store" }
    );
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const client = await getClient(id);
  return {
    title: client ? `${client.name} - Client` : "Client",
    robots: { index: false },
  };
}

export default async function ClientDetailPage({ params }: Props) {
  const { id } = await params;
  const client = await getClient(id);

  if (!client) notFound();

  let brandVoice: {
    tone?: string;
    cadence?: string;
    banned_jargon?: string[];
    sample_phrases?: string[];
  } | null = null;

  try {
    brandVoice = client.brand_voice_json
      ? JSON.parse(client.brand_voice_json)
      : null;
  } catch {
    brandVoice = null;
  }

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

      {/* Header */}
      <header className="flex items-start justify-between mb-10">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink mb-1">
            {client.name}
          </h1>
          <a
            href={client.website_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-graphite font-mono hover:text-ink underline underline-offset-2"
          >
            {client.website_url}
          </a>
        </div>
        <IngestButton clientId={client.id} />
      </header>

      {/* Brand Voice Profile */}
      <section>
        <h2 className="font-display text-xl font-bold text-ink mb-6">
          Brand Voice Profile
        </h2>

        {!brandVoice ? (
          <div className="border border-border p-10 text-center">
            <RefreshCw className="size-6 text-graphite mx-auto mb-3" aria-hidden="true" />
            <p className="text-sm text-graphite font-mono mb-2">
              No brand voice profile yet.
            </p>
            <p className="text-xs text-graphite font-mono">
              Run brand ingestion to extract tone and voice from the website and past content.
            </p>
          </div>
        ) : (
          <div className="border border-border divide-y divide-border">
            {brandVoice.tone && (
              <div className="p-6">
                <p className="text-xs font-mono text-graphite uppercase tracking-wider mb-2">
                  Tone
                </p>
                <p className="text-sm text-ink font-mono">{brandVoice.tone}</p>
              </div>
            )}
            {brandVoice.cadence && (
              <div className="p-6">
                <p className="text-xs font-mono text-graphite uppercase tracking-wider mb-2">
                  Cadence
                </p>
                <p className="text-sm text-ink font-mono">{brandVoice.cadence}</p>
              </div>
            )}
            {brandVoice.banned_jargon && brandVoice.banned_jargon.length > 0 && (
              <div className="p-6">
                <p className="text-xs font-mono text-graphite uppercase tracking-wider mb-3">
                  Banned Jargon
                </p>
                <div className="flex flex-wrap gap-2">
                  {brandVoice.banned_jargon.map((word) => (
                    <span
                      key={word}
                      className="text-xs font-mono border border-danger/30 text-danger bg-danger/5 px-2 py-0.5"
                    >
                      {word}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {brandVoice.sample_phrases && brandVoice.sample_phrases.length > 0 && (
              <div className="p-6">
                <p className="text-xs font-mono text-graphite uppercase tracking-wider mb-3">
                  Sample Phrases
                </p>
                <ul className="space-y-2">
                  {brandVoice.sample_phrases.map((phrase, i) => (
                    <li key={i} className="text-sm text-ink font-mono border-l-2 border-highlight pl-4">
                      &ldquo;{phrase}&rdquo;
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>
    </>
  );
}
