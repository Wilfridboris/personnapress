import type { Metadata } from "next";
import { cookies } from "next/headers";
import { ClientList } from "@/components/clients/ClientList";
import type { ClientListResponse } from "@/lib/types";

export const metadata: Metadata = {
  title: "Clients - PersonnaPress",
  robots: { index: false },
};

async function getClients(): Promise<ClientListResponse | null> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get("session");
  if (!sessionCookie) return null;

  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const res = await fetch(`${apiUrl}/api/v1/clients`, {
      headers: { Cookie: `session=${sessionCookie.value}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function ClientsPage() {
  const data = await getClients();

  const clients = data?.clients ?? [];
  const planAtLimit = data?.plan_at_limit ?? false;
  const planTier = data?.plan_tier ?? "starter";
  const clientLimit = data?.client_limit ?? 3;

  return (
    <ClientList
      clients={clients}
      planAtLimit={planAtLimit}
      planTier={planTier}
      clientLimit={clientLimit}
    />
  );
}
