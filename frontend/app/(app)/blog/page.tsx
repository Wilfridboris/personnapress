import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { BlogList } from "./blog-list";

export default async function BlogPage() {
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  // Server component does auth check ONLY (RSC loop rule).
  // Active client ID is read from the Zustand store in the client component.
  return <BlogList />;
}
