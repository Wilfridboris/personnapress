"use client";

import { useActionState, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchAPI, APIError } from "@/lib/api";
import type { ClientResponse } from "@/lib/types";

type FormState = {
  nameError?: string;
  formError?: string;
  upgradeMessage?: string;
} | null;

const inputClass =
  "w-full bg-transparent border-b border-[#111111] focus:border-b-2 outline-none py-2 text-[0.9375rem] text-[#111111] placeholder:text-[#555555]";

const labelClass =
  "block text-xs font-sans text-[#111111] uppercase tracking-widest mb-2";

function UpgradePrompt({ message }: { message: string }) {
  const [loading, setLoading] = useState(false);
  const [portalError, setPortalError] = useState(false);

  async function openPortal() {
    setLoading(true);
    setPortalError(false);
    try {
      const data = await fetchAPI<{ portal_url: string }>("/subscriptions/portal", {
        method: "POST",
      });
      window.location.href = data.portal_url;
    } catch {
      setPortalError(true);
      setLoading(false);
    }
  }

  return (
    <div role="alert" className="mb-6 border border-[#E5E5E5] p-4">
      <p className="text-sm text-[#111111] mb-3">{message}</p>
      {portalError && (
        <p className="text-xs text-[#8B0000] mb-2">
          Could not open the portal. Please try again or contact support.
        </p>
      )}
      <button
        type="button"
        onClick={openPortal}
        disabled={loading}
        className="text-sm border border-[#111111] text-[#111111] px-4 py-2 hover:bg-[#111111] hover:text-white transition-colors rounded-none disabled:opacity-50"
      >
        {loading ? "Opening..." : "Manage subscription"}
      </button>
    </div>
  );
}

export function CreateClientForm() {
  const router = useRouter();

  async function action(_prev: FormState, formData: FormData): Promise<FormState> {
    const name = (formData.get("name") as string) ?? "";
    const website_url = (formData.get("website_url") as string) ?? "";

    if (!name.trim()) {
      return { nameError: "Client name is required." };
    }

    try {
      const client = await fetchAPI<ClientResponse>("/clients", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          website_url: website_url.trim() || undefined,
        }),
      });
      router.push(`/clients/${client.id}`);
      return null;
    } catch (err) {
      if (err instanceof APIError && err.code === "CLIENT_LIMIT_REACHED") {
        return { upgradeMessage: err.message };
      }
      const message =
        err instanceof APIError ? err.message : "Something went wrong.";
      return { formError: message };
    }
  }

  const [state, dispatch, isPending] = useActionState(action, null);

  return (
    <form action={dispatch} noValidate>
      <h1 className="font-serif text-[2.25rem] font-bold tracking-[-0.01em] text-[#111111] mb-6">
        New client
      </h1>

      <hr className="border-[#E5E5E5] my-6" />

      {state?.formError && (
        <p role="alert" className="text-[#8B0000] text-sm mb-6">
          {state.formError}
        </p>
      )}

      {state?.upgradeMessage && (
        <UpgradePrompt message={state.upgradeMessage} />
      )}

      <div className="space-y-8">
        <div>
          <label htmlFor="name" className={labelClass}>
            Client name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            required
            autoComplete="organization"
            disabled={isPending}
            aria-describedby={state?.nameError ? "name-error" : undefined}
            aria-invalid={!!state?.nameError}
            className={inputClass}
          />
          {state?.nameError && (
            <p id="name-error" className="text-[#8B0000] text-xs mt-1">
              {state.nameError}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="website_url" className={labelClass}>
            Website URL
          </label>
          <p className="text-sm text-[#555555] mb-2">
            Recommended — for automatic voice setup
          </p>
          <input
            id="website_url"
            name="website_url"
            type="url"
            disabled={isPending}
            className={inputClass}
          />
        </div>
      </div>

      <div className="mt-10 flex items-center gap-6">
        <button
          type="submit"
          disabled={isPending}
          className="bg-[#111111] text-white px-5 py-2.5 border border-[#111111] shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-[#111111] transition-colors rounded-none font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Create client"
        >
          {isPending ? "Creating..." : "Create client"}
        </button>
        <Link
          href="/clients"
          className="text-sm text-[#555555] hover:underline"
          tabIndex={isPending ? -1 : 0}
        >
          Skip — set this up later
        </Link>
      </div>
    </form>
  );
}
