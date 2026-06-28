"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { fetchAPI, APIError } from "@/lib/api";
import { logout } from "@/lib/auth";

export function AccountClient() {
  const router = useRouter();
  const [portalLoading, setPortalLoading] = useState(false);
  const [logoutLoading, setLogoutLoading] = useState(false);
  const [error, setError] = useState("");

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

      {error && (
        <p role="alert" className="font-body text-sm text-danger mb-4">
          {error}
        </p>
      )}

      <Button
        variant="primary"
        onClick={handleManageSubscription}
        disabled={portalLoading}
        className="w-full"
      >
        {portalLoading ? "Loading..." : "Manage subscription"}
      </Button>

      <hr className="border-[#E5E5E5] my-6" />

      <Button
        variant="secondary"
        onClick={handleLogout}
        disabled={logoutLoading}
        className="w-full"
      >
        {logoutLoading ? "Logging out..." : "Log out"}
      </Button>
    </>
  );
}
