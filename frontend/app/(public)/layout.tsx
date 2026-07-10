import { PublicHeader } from "@/components/marketing/PublicHeader";
import { PublicFooter } from "@/components/marketing/PublicFooter";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-paper flex flex-col">
      <PublicHeader />
      <main className="flex-1 px-4 py-8">
        {children}
      </main>
      <PublicFooter />
    </div>
  );
}
