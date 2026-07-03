import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { PlatformConnectionsClient } from "@/components/publishing/PlatformConnectionsClient";

type Props = { params: Promise<{ id: string }> };

async function getClientName(id: string, session: string): Promise<string | null> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/clients/${id}`,
      { headers: { Cookie: `session=${session}` }, cache: "no-store" }
    );
    if (!res.ok) return null;
    const data = await res.json();
    return data.name ?? null;
  } catch {
    return null;
  }
}

export default async function PlatformConnectionsPage({ params }: Props) {
  const { id } = await params;

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  const clientName = await getClientName(id, session);
  if (!clientName) notFound();

  return (
    <div className="max-w-[720px] mx-auto px-8 py-10">
      <h1 className="font-serif text-[2.25rem] font-bold tracking-[-0.01em] text-[#111111] mb-1">
        Platform Connections
      </h1>
      <p className="text-[#555555] text-sm mb-8">{clientName}</p>
      <PlatformConnectionsClient clientId={id} />
    </div>
  );
}
