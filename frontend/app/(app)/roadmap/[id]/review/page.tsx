import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { RoadmapReviewClient } from "@/components/roadmap/RoadmapReviewClient";

type Props = { params: Promise<{ id: string }> };

export default async function RoadmapReviewPage({ params }: Props) {
  const { id } = await params;

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  return <RoadmapReviewClient roadmapId={id} />;
}
