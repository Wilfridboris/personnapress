import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ArticleEditor } from "../../blog/[id]/article-editor";

type Props = { params: Promise<{ id: string }> };

export default async function ArticleEditorPage({ params }: Props) {
  const { id } = await params;

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  if (!session) redirect("/login");

  // Server component does auth/session check ONLY (RSC loop rule).
  // All article and revision data fetched via TanStack Query in the client component.
  return <ArticleEditor articleId={id} />;
}
