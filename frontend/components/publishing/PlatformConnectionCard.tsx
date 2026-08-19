"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Building2, ExternalLink, Loader2, Lock, Sparkles, User } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { GitHubConnect } from "@/components/publishing/GitHubConnect";
import { publishingApi } from "@/lib/api";
import type { LinkedInOrg, PlatformConnectionStatus, ConnectionCreatePayload } from "@/lib/types";

interface Props {
  clientId: string;
  connection: PlatformConnectionStatus;
}

const PLATFORM_LABELS: Record<string, string> = {
  wordpress: "WordPress",
  webflow: "Webflow",
  x: "X (Twitter)",
  linkedin: "LinkedIn",
  github_pages: "GitHub Pages",
  instagram: "Instagram",
  facebook_page: "Facebook Page",
  threads: "Threads",
};


export function PlatformConnectionCard({ clientId, connection }: Props) {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [showDisconnect, setShowDisconnect] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wpType, setWpType] = useState<null | "self-hosted" | "wordpress-com">(null);

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

  // LinkedIn target picker state
  const [showTargetPicker, setShowTargetPicker] = useState(false);
  const [pickerTarget, setPickerTarget] = useState<"personal" | "organization">("personal");
  const [orgs, setOrgs] = useState<LinkedInOrg[] | null>(null);
  const [orgsLoading, setOrgsLoading] = useState(false);
  const [orgsError, setOrgsError] = useState<string | null>(null);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [selectedOrgName, setSelectedOrgName] = useState<string>("");
  const [savingTarget, setSavingTarget] = useState(false);
  const [targetError, setTargetError] = useState<string | null>(null);

  const orgPostingEnabled = process.env.NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED === "true";

  const disconnectTriggerRef = useRef<HTMLButtonElement>(null);
  const connectTriggerRef = useRef<HTMLButtonElement>(null);

  const label = PLATFORM_LABELS[connection.platform] ?? connection.platform;
  const isOAuth = connection.platform === "x" || connection.platform === "linkedin";
  const isGitHub = connection.platform === "github_pages";
  const isMetaPlatform =
    connection.platform === "instagram" ||
    connection.platform === "facebook_page" ||
    connection.platform === "threads";

  if (isGitHub) {
    return <GitHubConnect clientId={clientId} connection={connection} />;
  }

  function handleCancel() {
    setShowForm(false);
    setWpType(null);
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

  function handleOpenTargetPicker() {
    setPickerTarget(connection.linkedin_target === "organization" ? "organization" : "personal");
    setSelectedOrgId("");
    setSelectedOrgName("");
    setOrgs(null);
    setOrgsError(null);
    setTargetError(null);
    setShowTargetPicker(true);
  }

  function handleCancelPicker() {
    setShowTargetPicker(false);
    setOrgs(null);
    setOrgsError(null);
    setTargetError(null);
  }

  async function handleSelectCompanyPage() {
    if (!orgPostingEnabled) return;
    setPickerTarget("organization");
    if (orgs === null && !orgsLoading) {
      setOrgsLoading(true);
      setOrgsError(null);
      try {
        const result = await publishingApi.getLinkedInOrganizations(clientId);
        setOrgs(result.organizations);
        if (result.organizations.length > 0) {
          setSelectedOrgId(result.organizations[0].id);
          setSelectedOrgName(result.organizations[0].name);
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Failed to load pages.";
        if (msg === "token_insufficient_scope" || (e as { code?: string })?.code === "token_insufficient_scope") {
          setOrgsError("token_insufficient_scope");
        } else {
          setOrgsError(msg);
        }
      } finally {
        setOrgsLoading(false);
      }
    }
  }

  async function handleSaveTarget() {
    setSavingTarget(true);
    setTargetError(null);
    try {
      if (pickerTarget === "organization") {
        await publishingApi.updateLinkedInTarget(clientId, {
          target: "organization",
          org_id: selectedOrgId,
          org_name: selectedOrgName,
        });
      } else {
        await publishingApi.updateLinkedInTarget(clientId, { target: "personal" });
      }
      await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
      setShowTargetPicker(false);
    } catch (e: unknown) {
      setTargetError(e instanceof Error ? e.message : "Failed to save target.");
    } finally {
      setSavingTarget(false);
    }
  }

  async function handleDisconnect() {
    setLoading(true);
    try {
      const platformToDelete = connection.connected_via === "wordpress-com"
        ? "wordpress-com"
        : connection.platform;
      await publishingApi.deleteConnection(clientId, platformToDelete);
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
            <PlatformIcon platform={connection.platform} className="size-5 shrink-0" color={connection.connected ? "brand" : "mono"} />
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
                    {connection.platform === "linkedin" && (
                      <>
                        <span className="block text-xs text-[#555555] mt-0.5">
                          Posting as:{" "}
                          {connection.linkedin_target === "organization" && connection.linkedin_org_name
                            ? connection.linkedin_org_name
                            : "Personal Account"}
                          {" "}
                          <button
                            onClick={handleOpenTargetPicker}
                            className="underline underline-offset-2 hover:text-[#111111] transition-colors"
                          >
                            Change
                          </button>
                        </span>
                        {orgPostingEnabled && connection.linkedin_org_capable === false && (
                          <span className="mt-1.5 flex items-start gap-1.5 text-xs text-[#555555]">
                            <Sparkles className="size-3.5 shrink-0 mt-px text-[#2E4F2E]" aria-hidden="true" />
                            <span className="text-pretty">
                              New: publish to a Company Page you manage.{" "}
                              <a
                                href={`/api/auth/linkedin?client_id=${clientId}`}
                                className="inline-flex items-center gap-1 text-[#111111] underline underline-offset-2 hover:text-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                              >
                                Reconnect to enable.
                                <ExternalLink className="size-3 shrink-0" aria-hidden="true" />
                              </a>
                            </span>
                          </span>
                        )}
                      </>
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
            ) : isMetaPlatform ? null : isOAuth ? (
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

        {showTargetPicker && connection.platform === "linkedin" && (
          <div className="border-t border-[#E5E5E5] mt-4 pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-[#111111]">Posting destination</p>
              <button
                onClick={handleCancelPicker}
                className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
              >
                Cancel
              </button>
            </div>

            {/* Personal Account option */}
            <button
              type="button"
              onClick={() => {
                setPickerTarget("personal");
                if (!orgPostingEnabled) handleCancelPicker();
              }}
              className={`w-full text-left px-3 py-2.5 border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 ${
                pickerTarget === "personal"
                  ? "border-[#111111] ring-1 ring-[#111111]"
                  : "border-[#E5E5E5] hover:border-[#111111]"
              }`}
            >
              <div className="flex items-center gap-2">
                <User className="size-4 shrink-0 text-[#111111]" />
                <div>
                  <span className="block text-sm font-medium text-[#111111]">Personal Account</span>
                  <span className="block text-xs text-[#555555]">Your LinkedIn profile</span>
                </div>
              </div>
            </button>

            {/* Company Page option */}
            <button
              type="button"
              onClick={handleSelectCompanyPage}
              disabled={!orgPostingEnabled}
              className={`w-full text-left px-3 py-2.5 border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 ${
                !orgPostingEnabled
                  ? "opacity-50 cursor-not-allowed border-[#E5E5E5]"
                  : pickerTarget === "organization"
                  ? "border-[#111111] ring-1 ring-[#111111]"
                  : "border-[#E5E5E5] hover:border-[#111111]"
              }`}
              title={
                !orgPostingEnabled
                  ? "Company page posting requires LinkedIn Marketing Developer Platform approval. Currently only personal profile posting is available."
                  : undefined
              }
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Building2 className="size-4 shrink-0 text-[#111111]" />
                  <div>
                    <span className="block text-sm font-medium text-[#111111]">Company Page</span>
                    <span className="block text-xs text-[#555555]">
                      {orgPostingEnabled
                        ? "A LinkedIn Page you admin"
                        : "Requires LinkedIn Marketing Developer Platform approval"}
                    </span>
                  </div>
                </div>
                {!orgPostingEnabled && (
                  <Lock className="size-3.5 shrink-0 text-[#555555]" />
                )}
              </div>
            </button>

            {/* Org list — only when feature enabled and company page selected */}
            {orgPostingEnabled && pickerTarget === "organization" && (
              <div className="pl-1 space-y-2">
                {orgsLoading && (
                  <div className="flex items-center gap-2 py-2">
                    <Loader2 className="size-3.5 animate-spin text-[#555555]" />
                    <span className="text-xs text-[#555555]">Loading your pages...</span>
                  </div>
                )}
                {!orgsLoading && orgsError === "token_insufficient_scope" && (
                  <p className="text-xs text-[#555555]">
                    Please{" "}
                    <a
                      href={`/api/auth/linkedin?client_id=${clientId}`}
                      className="underline underline-offset-2 hover:text-[#111111] transition-colors"
                    >
                      reconnect LinkedIn
                    </a>{" "}
                    to enable company page access.
                  </p>
                )}
                {!orgsLoading && orgsError && orgsError !== "token_insufficient_scope" && (
                  <p className="text-xs text-[#C0392B]" role="alert">{orgsError}</p>
                )}
                {!orgsLoading && !orgsError && orgs !== null && orgs.length === 0 && (
                  <p className="text-xs text-[#555555]">
                    No pages found. You must be an admin of a LinkedIn Page to post to it.
                  </p>
                )}
                {!orgsLoading && !orgsError && orgs !== null && orgs.length > 0 && (
                  <div className="space-y-1">
                    {orgs.map((org) => (
                      <button
                        key={org.id}
                        type="button"
                        onClick={() => { setSelectedOrgId(org.id); setSelectedOrgName(org.name); }}
                        className={`w-full text-left px-3 py-2 border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 ${
                          selectedOrgId === org.id
                            ? "border-[#111111] ring-1 ring-[#111111]"
                            : "border-[#E5E5E5] hover:border-[#111111]"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Building2 className="size-4 shrink-0 text-[#555555]" />
                          <div>
                            <span className="block text-sm font-medium text-[#111111]">{org.name}</span>
                            <span className="block text-xs text-[#555555]">{org.follower_count.toLocaleString()} followers</span>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {targetError && (
              <p className="text-xs text-[#C0392B]" role="alert">{targetError}</p>
            )}

            {/* Save/Cancel buttons — shown when feature enabled */}
            {orgPostingEnabled && (
              <div className="flex gap-3 pt-1">
                <Button
                  variant="primary"
                  onClick={handleSaveTarget}
                  disabled={savingTarget || (pickerTarget === "organization" && !selectedOrgId)}
                  className="text-xs px-4 py-2"
                >
                  {savingTarget ? "Saving..." : "Save"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={handleCancelPicker}
                  className="text-xs px-4 py-2"
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>
        )}

        {showForm && (
          <div className="mt-4 pt-4 border-t border-[#E5E5E5] space-y-4">
            {connection.platform === "wordpress" && wpType === null && (
              <fieldset>
                <div className="flex items-center justify-between mb-3">
                  <legend className="text-xs font-medium text-[#111111]">
                    Where is your WordPress site hosted?
                  </legend>
                  <button type="button" onClick={handleCancel}
                    className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors">
                    Cancel
                  </button>
                </div>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => setWpType("self-hosted")}
                    className="w-full text-left px-4 py-3 border border-[#E5E5E5] hover:border-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 transition-colors duration-150"
                    aria-label="Self-hosted WordPress: your own server or managed host"
                  >
                    <span className="block text-sm font-medium text-[#111111]">Self-hosted WordPress</span>
                    <span className="block text-xs text-[#555555] mt-0.5">
                      Your own server or managed host: SiteGround, WP Engine, Kinsta, etc.
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setWpType("wordpress-com")}
                    className="w-full text-left px-4 py-3 border border-[#E5E5E5] hover:border-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 transition-colors duration-150"
                    aria-label="WordPress.com: free or paid site hosted by Automattic"
                  >
                    <span className="block text-sm font-medium text-[#111111]">WordPress.com</span>
                    <span className="block text-xs text-[#555555] mt-0.5">
                      Free or paid site hosted by Automattic at wordpress.com
                    </span>
                  </button>
                </div>
              </fieldset>
            )}

            {connection.platform === "wordpress" && wpType === "self-hosted" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <button type="button" onClick={() => setWpType(null)}
                    className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
                    aria-label="Back to WordPress hosting type selection">
                    Back
                  </button>
                  <button type="button" onClick={handleCancel}
                    className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors">
                    Cancel
                  </button>
                </div>
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

            {connection.platform === "wordpress" && wpType === "wordpress-com" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <button type="button" onClick={() => setWpType(null)}
                    className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
                    aria-label="Back to WordPress hosting type selection">
                    Back
                  </button>
                  <button type="button" onClick={handleCancel}
                    className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors">
                    Cancel
                  </button>
                </div>
                <p className="text-xs text-[#555555]">
                  You will be redirected to WordPress.com to authorize access.
                </p>
                <a
                  href={`/api/auth/wordpress-com?client_id=${clientId}`}
                  onClick={() => setLoading(true)}
                  className="inline-block px-5 py-2.5 border border-[#111111] text-[#111111] text-xs font-medium hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                  aria-label="Connect with WordPress.com via OAuth"
                >
                  {loading ? "Connecting…" : "Connect with WordPress.com"}
                </a>
              </div>
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

            {connection.platform === "webflow" && (
              <>
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
              </>
            )}
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
