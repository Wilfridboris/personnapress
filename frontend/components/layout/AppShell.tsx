"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useUIStore } from "@/lib/stores/useUIStore";
import { useClientStore } from "@/lib/stores/useClientStore";
import { clientsApi, subscriptionsApi } from "@/lib/api";
import { Sidebar } from "./sidebar";
import { MobileTopBar } from "./MobileTopBar";
import { MobileDrawer } from "./MobileDrawer";
import { TrialNudgeToast } from "./TrialNudgeToast";
import { UpgradePromptModal } from "@/components/common/UpgradePromptModal";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const closeMobileDrawer = useUIStore((s) => s.closeMobileDrawer);
  const queryClient = useQueryClient();

  useEffect(() => {
    closeMobileDrawer();
  }, [pathname, closeMobileDrawer]);

  useEffect(() => {
    subscriptionsApi
      .getStatus()
      .then(({ status }) => {
        if (status === "trial_expired") {
          queryClient.invalidateQueries({ queryKey: ["subscription"] });
        }
      })
      .catch(() => {/* silent — banner updates on next query refetch */});
  }, [queryClient]);

  useEffect(() => {
    async function initClients() {
      try {
        const data = await clientsApi.list();
        const { clients } = data;
        const store = useClientStore.getState();
        store.setClients(clients);

        const currentId = store.activeClientId;
        if (!currentId || !clients.some((c) => c.id === currentId)) {
          if (clients.length > 0) {
            store.setActiveClientId(clients[0].id);
          }
        }
      } catch {
        // silently fail — store remains empty
      } finally {
        useClientStore.getState().setInitialized();
      }
    }

    initClients();
  }, []);

  return (
    <div className="min-h-screen bg-[#F9F9F6]">
      <Sidebar />
      <MobileTopBar />
      <MobileDrawer />
      <TrialNudgeToast />
      <UpgradePromptModal />
      <main className="md:ml-14 lg:ml-60 pt-14 lg:pt-0 min-h-screen">
        <div className="max-w-5xl px-8 lg:px-12 py-8 mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
