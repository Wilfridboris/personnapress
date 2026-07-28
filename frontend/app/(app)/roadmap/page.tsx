import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { RoadmapListClient } from "@/components/roadmap/RoadmapListClient";

export default async function RoadmapListPage() {
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  return <RoadmapListClient />;
}
