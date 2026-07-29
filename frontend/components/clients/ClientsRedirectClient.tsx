"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useClientStore } from "@/lib/stores/useClientStore";

export function ClientsRedirectClient() {
  const router = useRouter();
  const activeClientId = useClientStore((s) => s.activeClientId);
  const isInitialized = useClientStore((s) => s.isInitialized);

  useEffect(() => {
    if (!isInitialized) return;
    router.replace(activeClientId ? `/clients/${activeClientId}` : "/dashboard");
  }, [activeClientId, isInitialized, router]);

  return null;
}
