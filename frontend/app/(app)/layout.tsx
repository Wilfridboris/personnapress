import { AppShell } from "@/components/layout/AppShell";
import { TrialBanner } from "@/components/layout/TrialBanner";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TrialBanner />
      <AppShell>{children}</AppShell>
    </>
  );
}
