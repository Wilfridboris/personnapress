"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { jobsApi, clientsApi } from "@/lib/api";
import { useJobStatus, isJobTerminal } from "@/hooks/useJobStatus";
import { useClientStore } from "@/lib/stores/useClientStore";
import type { BrandVoiceProfileStatus } from "@/lib/types";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { FileUploadPanel } from "@/components/clients/FileUploadPanel";
import { ClientDetailTabs } from "@/components/clients/ClientDetailTabs";
import { PlatformConnectionsClient } from "@/components/publishing/PlatformConnectionsClient";
import type { ClientResponse } from "@/lib/types";

interface Props {
  client: ClientResponse;
}

const secondaryBtn =
  "text-sm border border-[#111111] text-[#111111] px-4 py-2 hover:bg-[#111111] hover:text-white transition-colors rounded-none font-medium";

/** Cycle between two status messages while ingestion is running. */
function useIngestionMessage(domain: string, isIngesting: boolean): string {
  const [phase, setPhase] = useState<0 | 1>(0);

  useEffect(() => {
    if (!isIngesting) {
      setPhase(0);
      return;
    }
    const messages = [
      `Scraping ${domain}...`,
      "Extracting voice profile...",
    ];
    // Switch to second message after 5 s; cycle back after another 5 s
    const id = setInterval(() => {
      setPhase((prev) => (prev === 0 ? 1 : 0) as 0 | 1);
    }, 5000);
    return () => clearInterval(id);
  }, [isIngesting, domain]);

  if (!isIngesting) return "";
  const messages = [`Scraping ${domain}...`, "Extracting voice profile..."];
  return messages[phase];
}

export function ClientDetail({ client }: Props) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // ── Ensure current client is registered in the store ─────────────────────
  useEffect(() => {
    const store = useClientStore.getState();
    const bvpStatus: BrandVoiceProfileStatus = client.job_id
      ? "analyzing"
      : client.brand_voice_profile
        ? "ready"
        : "incomplete";
    const clientData = {
      id: client.id,
      name: client.name,
      website_url: client.website_url,
      brand_voice_profile_status: bvpStatus,
      campaign_count: client.campaign_count,
      brand_voice_profile: client.brand_voice_profile,
    };
    if (!store.clients.some((c) => c.id === client.id)) {
      store.addClient(clientData);
    } else {
      store.updateClient(client.id, clientData);
    }
    store.setActiveClientId(client.id);
  }, [client.id, client.name, client.website_url, client.brand_voice_profile, client.job_id, client.campaign_count]);

  // ── Active job ID ─────────────────────────────────────────────────────────
  const [jobId, setJobId] = useState<string | null>(client.job_id);

  // ── React Query polling via useJobStatus ─────────────────────────────────
  const { job } = useJobStatus(jobId);

  // When job completes: refresh client data and update store with BVP
  useEffect(() => {
    if (!job) return;
    if (job.status === "completed" || job.status === "complete") {
      queryClient.invalidateQueries({ queryKey: ["client", client.id] });
      setHasVoiceProfile(true);
      clientsApi.get(client.id).then((updated) => {
        useClientStore.getState().updateClient(client.id, {
          brand_voice_profile_status: "ready",
          brand_voice_profile: updated.brand_voice_profile,
        });
      }).catch(() => {
        // At minimum mark the status ready so campaigns/new shows correctly
        useClientStore.getState().updateClient(client.id, {
          brand_voice_profile_status: "ready",
        });
      });
    }
  }, [job, client.id, queryClient]);

  const isIngesting =
    !!jobId && (!job || job.status === "pending" || job.status === "in_progress");

  const jobFailed = !!job && job.status === "failed";

  // ── Voice profile local state ────────────────────────────────────────────
  const [hasVoiceProfile, setHasVoiceProfile] = useState(!!client.brand_voice_profile);

  // ── Ingestion status domain ───────────────────────────────────────────────
  const [websiteUrl, setWebsiteUrl] = useState(client.website_url ?? "");
  const domain = (() => {
    const url = websiteUrl.trim() || client.website_url || "";
    if (!url) return "";
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  })();

  const ingestionMessage = useIngestionMessage(domain, isIngesting);

  // ── Edit form ─────────────────────────────────────────────────────────────
  const [name, setName] = useState(client.name);
  const initialUrlRef = useRef(client.website_url ?? "");
  const [editError, setEditError] = useState<string | null>(null);
  const [editSaving, setEditSaving] = useState(false);

  // ── Re-analyze modal ──────────────────────────────────────────────────────
  const [showReAnalyzeModal, setShowReAnalyzeModal] = useState(false);
  const [reAnalyzing, setReAnalyzing] = useState(false);
  const saveBtnRef = useRef<HTMLButtonElement>(null);

  // ── Delete modal ──────────────────────────────────────────────────────────
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const deleteBtnRef = useRef<HTMLButtonElement>(null);

  const handleSave = async () => {
    setEditError(null);
    const urlChanged = websiteUrl.trim() !== initialUrlRef.current;

    if (urlChanged) {
      setShowReAnalyzeModal(true);
      return;
    }

    setEditSaving(true);
    try {
      const result = await clientsApi.patch(client.id, { name: name.trim() });
      if ("requires_confirmation" in result) return;
      setName(result.name);
      useClientStore.getState().updateClientName(client.id, result.name);
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setEditSaving(false);
    }
  };

  const handleConfirmReAnalyze = async () => {
    setReAnalyzing(true);
    try {
      const result = await clientsApi.patch(client.id, {
        name: name.trim(),
        website_url: websiteUrl.trim(),
        confirm_url_change: true,
      });
      if ("requires_confirmation" in result) return;
      setName(result.name);
      useClientStore.getState().updateClientName(client.id, result.name);
      initialUrlRef.current = websiteUrl.trim();
      setHasVoiceProfile(false);
      setShowReAnalyzeModal(false);
      if (result.job_id) {
        setJobId(String(result.job_id));
      }
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : "Failed to update URL.");
    } finally {
      setReAnalyzing(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await clientsApi.delete(client.id);
      useClientStore.getState().removeClient(client.id);
      router.push("/clients");
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : "Failed to delete client.");
      setShowDeleteModal(false);
    } finally {
      setDeleting(false);
    }
  };

  const reAnalyzeDomain = (() => {
    const url = websiteUrl.trim();
    if (!url) return "";
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  })();

  const profileContent = (
    <>
      {/* ── Edit client ─────────────────────────────────────────────────── */}
      <section aria-labelledby="edit-heading" className="mb-10">
        <h2
          id="edit-heading"
          className="font-serif text-lg font-bold text-ink mb-4"
        >
          Edit client
        </h2>

        <div className="space-y-4 max-w-md">
          <div>
            <label htmlFor="client-name" className="block text-xs uppercase tracking-widest text-graphite mb-1">
              Client name
            </label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              id="client-name"
            />
          </div>
          <div>
            <label htmlFor="client-website-url" className="block text-xs uppercase tracking-widest text-graphite mb-1">
              Website URL
            </label>
            <Input
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              type="url"
              id="client-website-url"
              placeholder="https://example.com"
            />
          </div>

          {editError && (
            <p role="alert" className="text-sm text-danger">
              {editError}
            </p>
          )}

          <Button
            ref={saveBtnRef}
            onClick={handleSave}
            disabled={editSaving}
            aria-busy={editSaving}
          >
            {editSaving ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </section>

      <hr className="border-border mb-10" />

      {/* ── Danger zone ─────────────────────────────────────────────────── */}
      <section aria-labelledby="danger-heading">
        <p
          id="danger-heading"
          className="text-xs font-sans uppercase tracking-widest text-ink mb-4"
        >
          Danger zone
        </p>
        <Button
          ref={deleteBtnRef}
          variant="danger"
          onClick={() => setShowDeleteModal(true)}
        >
          Delete client
        </Button>
      </section>
    </>
  );

  const voiceContent = (
    <>
      {/* ── Brand voice ────────────────────────────────────────────────── */}
      <section aria-labelledby="bvp-heading" className="mb-10">
        <p
          id="bvp-heading"
          className="text-xs font-sans uppercase tracking-widest text-ink mb-4"
        >
          Brand voice
        </p>

        {isIngesting ? (
          <p className="font-mono text-sm text-graphite animate-pulse">
            {ingestionMessage || `Scraping ${domain}...`}
          </p>
        ) : jobFailed ? (
          <div>
            <p className="text-sm text-graphite mb-4">
              {`Couldn't extract content from ${domain || "the website"}. Complete the voice questionnaire to set up your profile.`}
            </p>
            <Link
              href={`/clients/${client.id}/voice?mode=questionnaire`}
              className={secondaryBtn}
            >
              Complete questionnaire
            </Link>
          </div>
        ) : !hasVoiceProfile ? (
          <div>
            <p className="text-graphite mb-4">
              No voice profile yet. Upload content or complete the voice questionnaire.
            </p>
            <div className="flex gap-3">
              <Link href={`/clients/${client.id}/voice?mode=upload`} className={secondaryBtn}>
                Upload content
              </Link>
              <Link href={`/clients/${client.id}/voice?mode=questionnaire`} className={secondaryBtn}>
                Complete questionnaire
              </Link>
            </div>
          </div>
        ) : (
          <div className="border border-border divide-y divide-border">
            <div className="p-6">
              <p className="text-xs uppercase tracking-widest text-graphite mb-2">
                Profile ready
              </p>
              <p className="text-sm text-ink">Voice profile has been generated.</p>
            </div>
          </div>
        )}
      </section>

      <hr className="border-border mb-10" />

      {/* ── Content files ───────────────────────────────────────────────── */}
      <section className="mb-10">
        <FileUploadPanel clientId={client.id} />
      </section>
    </>
  );

  const connectionsContent = (
    <PlatformConnectionsClient clientId={client.id} />
  );

  return (
    <>
      <ClientDetailTabs
        profileContent={profileContent}
        voiceContent={voiceContent}
        connectionsContent={connectionsContent}
      />

      {/* ── Re-analyze confirmation modal ────────────────────────────── */}
      <ConfirmModal
        isOpen={showReAnalyzeModal}
        onClose={() => setShowReAnalyzeModal(false)}
        onConfirm={handleConfirmReAnalyze}
        title="Re-analyze voice profile?"
        description={`Updating the website URL will re-analyze ${reAnalyzeDomain}. This will overwrite your current voice profile. Continue?`}
        confirmLabel="Re-analyze"
        confirmVariant="primary"
        isLoading={reAnalyzing}
        triggerRef={saveBtnRef}
      />

      {/* ── Delete confirmation modal ────────────────────────────────── */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDelete}
        title={`Delete '${client.name}'?`}
        description={`This will remove ${client.campaign_count} campaign${client.campaign_count !== 1 ? "s" : ""} and all platform connections.`}
        confirmLabel="Delete client"
        confirmVariant="danger"
        isLoading={deleting}
        triggerRef={deleteBtnRef}
      />
    </>
  );
}
