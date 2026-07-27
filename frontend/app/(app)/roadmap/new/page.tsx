import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { PlanMyWeekClient } from "@/components/roadmap/PlanMyWeekClient";

export const metadata: Metadata = {
  title: "Plan My Week | PersonnaPress",
};

export default async function PlanMyWeekPage() {
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  return <PlanMyWeekClient />;
}
