import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { VoiceSetupPage } from "@/components/clients/VoiceSetupPage";
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
  if (!session) return { title: "Brand Voice — PersonnaPress" };
  const result = await getClient(id, session);
  const client = result === "expired" || result === null ? null : result;
  return {
    title: client
      ? `Brand Voice — ${client.name} — PersonnaPress`
      : "Brand Voice — PersonnaPress",
    robots: { index: false },
  };
}

export default async function VoicePage({ params }: Props) {
  const { id } = await params;

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  const result = await getClient(id, session);
  if (result === "expired") redirect("/login");
  if (!result) notFound();

  return <VoiceSetupPage client={result} />;
}
