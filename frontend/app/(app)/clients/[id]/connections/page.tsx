import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { PlatformConnectionsClient } from "@/components/publishing/PlatformConnectionsClient";

type Props = { params: Promise<{ id: string }> };

export default async function PlatformConnectionsPage({ params }: Props) {
  const { id } = await params;

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  return (
    <div className="max-w-[720px] mx-auto px-8 py-10">
      <PlatformConnectionsClient clientId={id} />
    </div>
  );
}
