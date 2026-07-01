import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { ClientDetail } from "@/components/clients/ClientDetail";
import type { ClientResponse } from "@/lib/types";

type Props = { params: Promise<{ id: string }> };

type GetClientResult = ClientResponse | "expired" | null;

async function getClient(id: string, session: string): Promise<GetClientResult> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/clients/${id}`,
      {
        headers: { Cookie: `session=${session}` },
        cache: "no-store",
      },
    );
    if (res.status === 401) return "expired";
    if (res.status === 403 || res.status === 404) return null;
    if (!res.ok) return null;
    return res.json() as Promise<ClientResponse>;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) return { title: "Client — PersonnaPress" };
  const result = await getClient(id, session);
  const client = result === "expired" || result === null ? null : result;
  return {
    title: client ? `${client.name} — PersonnaPress` : "Client — PersonnaPress",
    robots: { index: false },
  };
}

export default async function ClientDetailPage({ params }: Props) {
  const { id } = await params;

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  const result = await getClient(id, session);
  if (result === "expired") redirect("/login");
  if (!result) notFound();

  const client = result;

  return (
    <>
      <Link
        href="/clients"
        className="inline-flex items-center gap-2 text-sm text-[#555555] hover:text-[#111111] transition-colors mb-10"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to clients
      </Link>

      <header className="mb-10">
        <h1 className="font-serif text-[2.25rem] font-bold tracking-[-0.01em] text-[#111111] mb-1">
          {client.name}
        </h1>
        {client.website_url && (
          <a
            href={client.website_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-[#555555] hover:text-[#111111] underline underline-offset-2"
          >
            {client.website_url}
          </a>
        )}
      </header>

      <hr className="border-[#E5E5E5] my-6" />

      <ClientDetail client={client} />
    </>
  );
}
