import type { Metadata } from "next";
import Link from "next/link";
import { Plus, ArrowRight, Globe } from "lucide-react";

export const metadata: Metadata = {
  title: "Clients",
  robots: { index: false },
};

async function getClients() {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/clients`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function ClientsPage() {
  const clients = await getClients();

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <header className="flex items-center justify-between mb-10">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink mb-1">
            Clients
          </h1>
          <p className="text-sm text-graphite font-mono">
            Each client has its own brand voice profile.
          </p>
        </div>
        <Link
          href="/clients/new"
          className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-3 hover:bg-graphite transition-colors"
        >
          <Plus className="size-4" aria-hidden="true" />
          New Client
        </Link>
      </header>

      {clients.length === 0 ? (
        <div className="border border-border p-16 text-center">
          <Globe className="size-8 text-graphite mx-auto mb-4" aria-hidden="true" />
          <p className="text-graphite font-mono text-sm mb-2">
            No clients yet.
          </p>
          <p className="text-xs text-graphite font-mono mb-6">
            Create a client to start building a brand voice profile.
          </p>
          <Link
            href="/clients/new"
            className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-6 py-3 hover:bg-graphite transition-colors"
          >
            <Plus className="size-4" aria-hidden="true" />
            Create First Client
          </Link>
        </div>
      ) : (
        <div className="border border-border divide-y divide-border">
          {clients.map(
            (client: {
              id: number;
              name: string;
              website_url: string;
              brand_voice_json: string | null;
            }) => (
              <Link
                key={client.id}
                href={`/clients/${client.id}`}
                className="flex items-center justify-between p-6 hover:bg-ink/3 transition-colors group"
              >
                <div>
                  <p className="font-medium text-ink mb-1">{client.name}</p>
                  <p className="text-xs text-graphite font-mono">
                    {client.website_url}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={`text-xs font-mono border px-2 py-0.5 ${
                      client.brand_voice_json
                        ? "border-success/30 text-success bg-success/5"
                        : "border-border text-graphite"
                    }`}
                  >
                    {client.brand_voice_json ? "Voice profile ready" : "No profile yet"}
                  </span>
                  <ArrowRight
                    className="size-4 text-graphite opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-hidden="true"
                  />
                </div>
              </Link>
            )
          )}
        </div>
      )}
    </div>
  );
}
