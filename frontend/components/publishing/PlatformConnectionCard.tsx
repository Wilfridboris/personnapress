"use client";

import { useRef, useState } from "react";
import { Globe, LayoutGrid, Share2, Link2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { publishingApi } from "@/lib/api";
import type { PlatformConnectionStatus, ConnectionCreatePayload } from "@/lib/types";

interface Props {
  clientId: string;
  connection: PlatformConnectionStatus;
}

const PLATFORM_LABELS: Record<string, string> = {
  wordpress: "WordPress",
  webflow: "Webflow",
  x: "X (Twitter)",
  linkedin: "LinkedIn",
};

function PlatformIcon({ platform }: { platform: string }) {
  const cls = "size-5 shrink-0";
  if (platform === "wordpress") return <Globe className={cls} aria-hidden="true" />;
  if (platform === "webflow") return <LayoutGrid className={cls} aria-hidden="true" />;
  if (platform === "x") return <Share2 className={cls} aria-hidden="true" />;
  return <Link2 className={cls} aria-hidden="true" />;
}

export function PlatformConnectionCard({ clientId, connection }: Props) {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [showDisconnect, setShowDisconnect] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WordPress form state
  const [wpSiteUrl, setWpSiteUrl] = useState("");
  const [wpUsername, setWpUsername] = useState("");
  const [wpPassword, setWpPassword] = useState("");

  // Webflow form state
  const [wfToken, setWfToken] = useState("");
  const [wfCollections, setWfCollections] = useState<{ id: string; name: string }[] | null>(null);
  const [wfCollectionId, setWfCollectionId] = useState("");
  const [wfCollectionFetchFailed, setWfCollectionFetchFailed] = useState(false);
  const [wfValidating, setWfValidating] = useState(false);

  const disconnectTriggerRef = useRef<HTMLButtonElement>(null);
  const connectTriggerRef = useRef<HTMLButtonElement>(null);

  const label = PLATFORM_LABELS[connection.platform] ?? connection.platform;
  const isOAuth = connection.platform === "x" || connection.platform === "linkedin";

  function handleCancel() {
    setShowForm(false);
    setError(null);
    setWpSiteUrl("");
    setWpUsername("");
    setWpPassword("");
    setWfToken("");
    setWfCollections(null);
    setWfCollectionId("");
    setWfCollectionFetchFailed(false);
  }

  async function handleConnect() {
    setError(null);
    setLoading(true);
    try {
      let payload: ConnectionCreatePayload;
      if (connection.platform === "wordpress") {
        payload = { platform: "wordpress", site_url: wpSiteUrl, credential: wpPassword, username: wpUsername };
      } else {
        payload = { platform: "webflow", token: wfToken, collection_id: wfCollectionId };
      }
      await publishingApi.createConnection(clientId, payload);
      await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
      setShowForm(false);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Connection failed.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleValidateWebflowToken() {
    setWfCollectionFetchFailed(false);
    setWfCollections(null);
    setWfValidating(true);
    setError(null);
    try {
      const result = await publishingApi.getWebflowCollections(clientId, wfToken);
      setWfCollections(result.collections);
      if (result.collections.length > 0) {
        setWfCollectionId(result.collections[0].id);
      }
    } catch {
      setWfCollectionFetchFailed(true);
    } finally {
      setWfValidating(false);
    }
  }

  async function handleDisconnect() {
    setLoading(true);
    try {
      await publishingApi.deleteConnection(clientId, connection.platform);
      await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
      setShowDisconnect(false);
    } catch {
      setShowDisconnect(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div
        className={`bg-white border ${connection.connected ? "border-[#111111]" : "border-[#E5E5E5]"} rounded-none p-5`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <PlatformIcon platform={connection.platform} />
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.06em] text-[#111111]">{label}</p>
              <span aria-live="polite">
                {connection.connected ? (
                  <>
                    <span className="text-xs font-medium uppercase tracking-[0.06em] text-[#2E4F2E]">
                      Connected
                    </span>
                    {connection.account_identifier && (
                      <span className="block text-xs text-[#555555] mt-0.5">
                        {connection.account_identifier}
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-xs font-medium uppercase tracking-[0.06em] text-[#555555]">
                    Not connected
                  </span>
                )}
              </span>
            </div>
          </div>

          <div className="shrink-0">
            {connection.connected ? (
              <button
                ref={disconnectTriggerRef}
                onClick={() => setShowDisconnect(true)}
                className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
                aria-label={`Disconnect ${label}`}
              >
                Disconnect
              </button>
            ) : isOAuth ? (
              <a
                href={`/api/auth/${connection.platform}?client_id=${clientId}`}
                onClick={() => setLoading(true)}
                className="inline-block px-5 py-2.5 border border-[#111111] text-[#111111] text-xs font-medium rounded-none hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                aria-label={`Connect ${label}`}
              >
                {loading ? "Connecting..." : `Connect ${label}`}
              </a>
            ) : (
              <Button
                ref={connectTriggerRef}
                variant="secondary"
                onClick={() => { setShowForm(true); setError(null); }}
                aria-label={`Connect ${label}`}
                className="text-xs px-4 py-2"
              >
                Connect
              </Button>
            )}
          </div>
        </div>

        {showForm && (
          <div className="mt-4 pt-4 border-t border-[#E5E5E5] space-y-4">
            {connection.platform === "wordpress" && (
              <>
                <div className="space-y-1">
                  <label htmlFor={`wp-url-${connection.platform}`} className="block text-xs font-medium text-[#111111]">
                    WordPress site URL
                  </label>
                  <input
                    id={`wp-url-${connection.platform}`}
                    type="url"
                    value={wpSiteUrl}
                    onChange={(e) => setWpSiteUrl(e.target.value)}
                    placeholder="https://mysite.com"
                    className="w-full border-b border-[#111111] focus:border-b-2 outline-none bg-transparent py-2 text-sm text-[#111111] placeholder:text-[#999]"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor={`wp-user-${connection.platform}`} className="block text-xs font-medium text-[#111111]">
                    WordPress Username
                  </label>
                  <input
                    id={`wp-user-${connection.platform}`}
                    type="text"
                    value={wpUsername}
                    onChange={(e) => setWpUsername(e.target.value)}
                    placeholder="admin"
                    className="w-full border-b border-[#111111] focus:border-b-2 outline-none bg-transparent py-2 text-sm text-[#111111] placeholder:text-[#999]"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor={`wp-pass-${connection.platform}`} className="block text-xs font-medium text-[#111111]">
                    Application Password
                  </label>
                  <input
                    id={`wp-pass-${connection.platform}`}
                    type="password"
                    value={wpPassword}
                    onChange={(e) => setWpPassword(e.target.value)}
                    placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                    className="w-full border-b border-[#111111] focus:border-b-2 outline-none bg-transparent py-2 text-sm text-[#111111] placeholder:text-[#999]"
                  />
                </div>
              </>
            )}

            {connection.platform === "webflow" && (
              <>
                <div className="space-y-1">
                  <label htmlFor={`wf-token-${connection.platform}`} className="block text-xs font-medium text-[#111111]">
                    Webflow API Bearer Token
                  </label>
                  <input
                    id={`wf-token-${connection.platform}`}
                    type="text"
                    value={wfToken}
                    onChange={(e) => { setWfToken(e.target.value); setWfCollections(null); setWfCollectionFetchFailed(false); }}
                    className="w-full border-b border-[#111111] focus:border-b-2 outline-none bg-transparent py-2 text-sm text-[#111111]"
                  />
                </div>
                <Button
                  variant="secondary"
                  onClick={handleValidateWebflowToken}
                  disabled={!wfToken || wfValidating}
                  className="text-xs px-4 py-2"
                >
                  {wfValidating ? "Validating…" : "Validate token"}
                </Button>

                {wfCollections && !wfCollectionFetchFailed && (
                  <div className="space-y-1">
                    <label htmlFor="wf-collection" className="block text-xs font-medium text-[#111111]">
                      CMS Collection
                    </label>
                    <select
                      id="wf-collection"
                      value={wfCollectionId}
                      onChange={(e) => setWfCollectionId(e.target.value)}
                      className="w-full border-b border-[#111111] outline-none bg-transparent py-2 text-sm text-[#111111]"
                    >
                      {wfCollections.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                {wfCollectionFetchFailed && (
                  <div className="space-y-1">
                    <label htmlFor="wf-collection-manual" className="block text-xs font-medium text-[#111111]">
                      Webflow Collection ID
                    </label>
                    <input
                      id="wf-collection-manual"
                      type="text"
                      value={wfCollectionId}
                      onChange={(e) => setWfCollectionId(e.target.value)}
                      className="w-full border-b border-[#111111] focus:border-b-2 outline-none bg-transparent py-2 text-sm text-[#111111]"
                    />
                    <p className="text-xs text-[#555555]">
                      Find your Collection ID in Webflow &rarr; CMS &rarr; [Collection] &rarr; Settings
                    </p>
                  </div>
                )}
              </>
            )}

            {error && (
              <p className="text-xs text-[#C0392B]" role="alert">{error}</p>
            )}

            <div className="flex gap-3 pt-1">
              <Button
                variant="primary"
                onClick={handleConnect}
                disabled={loading}
                className="text-xs px-4 py-2"
              >
                {loading ? "Connecting…" : "Connect"}
              </Button>
              <Button
                variant="secondary"
                onClick={handleCancel}
                disabled={loading}
                className="text-xs px-4 py-2"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </div>

      <Modal
        isOpen={showDisconnect}
        onClose={() => setShowDisconnect(false)}
        title={`Disconnect ${label}?`}
        titleId="disconnect-dialog-heading"
        triggerRef={disconnectTriggerRef}
      >
        <p className="text-sm text-[#555555] mb-6">
          Future campaigns will not publish to this platform.
        </p>
        <div className="flex gap-3">
          <Button
            variant="danger"
            onClick={handleDisconnect}
            disabled={loading}
            aria-label={`Disconnect ${label}`}
          >
            {loading ? "Disconnecting…" : "Disconnect"}
          </Button>
          <Button variant="secondary" onClick={() => setShowDisconnect(false)}>
            Cancel
          </Button>
        </div>
      </Modal>
    </>
  );
}

export function PlatformConnectionCardSkeleton() {
  return (
    <div className="bg-white border border-[#E5E5E5] rounded-none p-5 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="size-5 bg-[#E5E5E5] rounded-sm" />
          <div className="space-y-1.5">
            <div className="h-2.5 w-20 bg-[#E5E5E5] rounded" />
            <div className="h-2 w-16 bg-[#E5E5E5] rounded" />
          </div>
        </div>
        <div className="h-8 w-20 bg-[#E5E5E5] rounded" />
      </div>
    </div>
  );
}
