"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { fetchAPI, APIError } from "@/lib/api";
import { logout } from "@/lib/auth";
import type { PlanTier } from "@/lib/types";
import { PlanPickerClient } from "./PlanPickerClient";

interface AccountClientProps {
  status: string;
  currentTier: PlanTier;
}

export function AccountClient({ status, currentTier }: AccountClientProps) {
  const router = useRouter();
  const [portalLoading, setPortalLoading] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);
  const [error, setError] = useState("");

  const showPlanPicker = status === "trialing" || status === "trial_expired";

  async function handleManageSubscription() {
    setPortalLoading(true);
    setError("");
    try {
      const data = await fetchAPI<{ portal_url: string }>("/subscriptions/portal", {
        method: "POST",
      });
      window.location.href = data.portal_url;
    } catch (err) {
      const message =
        err instanceof APIError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Something went wrong.";
      setError(message);
    } finally {
      setPortalLoading(false);
    }
  }

  async function handleLogout() {
    setLogoutLoading(true);
    try {
      await logout(router);
    } catch {
      // ignore — logout failure shouldn't block the UI
    } finally {
      setLogoutLoading(false);
    }
  }

  return (
    <>
      <hr className="border-[#E5E5E5] my-6" />

      {!showPlanPicker && error && (
        <p role="alert" className="font-body text-sm text-danger mb-4">
          {error}
        </p>
      )}

      {showPlanPicker ? (
        <PlanPickerClient currentTier={currentTier} />
      ) : (
        <Button
          variant="primary"
          onClick={handleManageSubscription}
          disabled={portalLoading}
          className="w-full"
        >
          {portalLoading ? "Loading..." : "Manage subscription"}
        </Button>
      )}

      <hr className="border-[#E5E5E5] my-6" />

      <Button
        variant="secondary"
        onClick={handleLogout}
        disabled={logoutLoading}
        className="w-full"
      >
        {logoutLoading ? "Logging out..." : "Log out"}
      </Button>

      <hr className="border-[#E5E5E5] my-6" />

      <Link
        href="/account/support"
        className="font-body text-sm text-graphite underline underline-offset-2 hover:text-ink transition-colors"
      >
        Help &amp; Support
      </Link>
    </>
  );
}
