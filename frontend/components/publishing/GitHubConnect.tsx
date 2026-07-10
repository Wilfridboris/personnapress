"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GitBranch } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { publishingApi } from "@/lib/api";
import type { GitHubDetectionResult, PlatformConnectionStatus } from "@/lib/types";

const FRAMEWORK_NAMES: Record<string, string> = {
  jekyll: "Jekyll",
  astro: "Astro",
  hugo: "Hugo",
  eleventy: "Eleventy",
  docusaurus: "Docusaurus",
  mkdocs: "MkDocs",
  nextjs: "Next.js",
  plain_static: "Plain Static",
};

const SELECTABLE_FRAMEWORKS = [
  "jekyll",
  "astro",
  "hugo",
  "eleventy",
  "docusaurus",
  "mkdocs",
  "nextjs",
  "plain_static",
];

function getPublishPathDisplay(framework: string, publishPath: string): string {
  if (!publishPath || publishPath === "/") return "slug.md";
  const base = publishPath.endsWith("/") ? publishPath : `${publishPath}/`;
  const filename = framework === "jekyll" ? "YYYY-MM-DD-slug.md" : "slug.md";
  return `${base}${filename}`;
}

interface Props {
  clientId: string;
  connection: PlatformConnectionStatus;
}

export function GitHubConnect({ clientId, connection }: Props) {
  const queryClient = useQueryClient();
  const [showDisconnect, setShowDisconnect] = useState(false);
  const [repoLoading, setRepoLoading] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [disconnectError, setDisconnectError] = useState<string | null>(null);
  const [detectionResult, setDetectionResult] = useState<GitHubDetectionResult | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);
  const [unknownFramework, setUnknownFramework] = useState<string>("jekyll");
  const [manualPublishPath, setManualPublishPath] = useState<string>("");
  const [directCommitDefault, setDirectCommitDefault] = useState<boolean>(connection.direct_commit_default ?? false);
  const disconnectTriggerRef = useRef<HTMLButtonElement>(null);

  const isConnectedNoRepo = connection.connected && !connection.account_identifier;
  const isConnectedWithRepo = connection.connected && !!connection.account_identifier;

  // Merge: fresh mutation result takes priority over stored credential data
  const activeDetection = detectionResult ?? connection.github_detection ?? null;

  const { data: reposData, isLoading: reposLoading } = useQuery({
    queryKey: ["github-repos", clientId],
    queryFn: () => publishingApi.listGitHubRepos(clientId),
    enabled: isConnectedNoRepo,
    staleTime: 60_000,
  });

  const detectMutation = useMutation({
    mutationFn: () => publishingApi.detectFramework(clientId),
    onSuccess: (data) => {
      setDetectionResult(data);
      setSelectedCandidate(data.candidates[0]?.framework ?? null);
      queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
    },
  });

  const frameworkMutation = useMutation({
    mutationFn: ({ framework, publishPath }: { framework: string; publishPath?: string }) =>
      publishingApi.setFramework(clientId, framework, publishPath),
    onSuccess: (data) => {
      setDetectionResult(data);
      setManualPublishPath("");
      queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
    },
  });

  const settingsMutation = useMutation({
    mutationFn: (directCommit: boolean) => publishingApi.updateGitHubSettings(clientId, directCommit),
    onSuccess: (_, directCommit) => {
      setDirectCommitDefault(directCommit);
      queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
    },
  });

  async function handleSelectRepo(repoFullName: string) {
    setRepoError(null);
    setRepoLoading(true);
    try {
      await publishingApi.selectGitHubRepo(clientId, repoFullName);
      await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
      detectMutation.mutate();
    } catch (e: unknown) {
      setRepoError(e instanceof Error ? e.message : "Failed to select repository.");
    } finally {
      setRepoLoading(false);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    setDisconnectError(null);
    try {
      await publishingApi.deleteConnection(clientId, "github_pages");
      await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
      setShowDisconnect(false);
      setDetectionResult(null);
    } catch (e: unknown) {
      setDisconnectError(e instanceof Error ? e.message : "Disconnect failed. Please try again.");
    } finally {
      setDisconnecting(false);
    }
  }

  function handleRescan() {
    setDetectionResult(null);
    detectMutation.mutate();
  }

  function handleConfirmCandidate() {
    const fw = selectedCandidate ?? activeDetection?.candidates[0]?.framework;
    if (fw) frameworkMutation.mutate({ framework: fw });
  }

  function handleConfirmUnknown() {
    frameworkMutation.mutate({ framework: unknownFramework });
  }

  function handleConfirmPublishPath() {
    const fw = activeDetection?.detected_framework ?? "nextjs";
    if (manualPublishPath.trim()) {
      frameworkMutation.mutate({ framework: fw, publishPath: manualPublishPath.trim() });
    }
  }

  const isAmbiguous = !!activeDetection?.candidates?.length;
  const isUnknown = !isAmbiguous && activeDetection?.detected_framework === "unknown";
  const isConfident = !!activeDetection && !isAmbiguous && !isUnknown;

  return (
    <>
      <div
        className={`bg-white border ${connection.connected ? "border-[#111111]" : "border-[#E5E5E5]"} rounded-none p-5`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <GitBranch className="size-5 shrink-0" aria-hidden="true" />
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.06em] text-[#111111]">GitHub Pages</p>
              <span aria-live="polite">
                {connection.connected ? (
                  <>
                    <span className="text-xs font-medium uppercase tracking-[0.06em] text-[#2E4F2E]">
                      Connected
                    </span>
                    {connection.account_identifier && (
                      <span className="block text-xs text-[#555555] mt-0.5 font-mono">
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
            {!connection.connected ? (
              <a
                href={`/api/auth/github?client_id=${clientId}`}
                className="inline-block px-5 py-2.5 border border-[#111111] text-[#111111] text-xs font-medium hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                aria-label="Connect GitHub"
              >
                Connect GitHub
              </a>
            ) : (
              <button
                ref={disconnectTriggerRef}
                onClick={() => setShowDisconnect(true)}
                className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
                aria-label="Disconnect GitHub"
              >
                Disconnect
              </button>
            )}
          </div>
        </div>

        {/* Repo selection — shown when connected but no repo chosen yet */}
        {isConnectedNoRepo && (
          <div className="mt-4 pt-4 border-t border-[#E5E5E5] space-y-3">
            <p className="text-xs font-medium text-[#111111]">Select a repository to publish to:</p>
            {reposLoading ? (
              <div
                className="h-8 w-48 bg-[#E5E5E5] rounded animate-pulse"
                aria-label="Loading repositories"
              />
            ) : reposData?.repos && reposData.repos.length > 0 ? (
              <>
                <select
                  defaultValue=""
                  onChange={(e) => e.target.value && handleSelectRepo(e.target.value)}
                  disabled={repoLoading}
                  className="w-full border-b border-[#111111] outline-none bg-transparent py-2 text-sm text-[#111111] font-mono"
                  aria-label="Select GitHub repository"
                >
                  <option value="" disabled>
                    Choose a repository…
                  </option>
                  {reposData.repos.map((repo) => (
                    <option key={repo.full_name} value={repo.full_name}>
                      {repo.full_name}{repo.private ? " (private)" : ""}
                    </option>
                  ))}
                </select>
                {repoError && (
                  <p className="text-xs text-[#C0392B]" role="alert">{repoError}</p>
                )}
              </>
            ) : (
              <p className="text-xs text-[#555555]">
                No repositories found. Make sure the GitHub App has access to at least one repository.
              </p>
            )}
          </div>
        )}

        {/* Detection area — shown when repo is selected */}
        {isConnectedWithRepo && (
          <div className="mt-4 pt-4 border-t border-[#E5E5E5]">
            {detectMutation.isPending ? (
              /* Scanning state */
              <div aria-live="polite">
                <p className="text-[13px] font-mono text-[#555555] mb-3">Scanning repository…</p>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-3 w-64" />
                  <Skeleton className="h-3 w-40" />
                </div>
              </div>
            ) : isConfident ? (
              /* Confident result */
              <div
                className="bg-white border border-[#E5E5E5] rounded-none p-4 hover:shadow-[4px_4px_0px_#111111] transition-shadow"
                aria-live="polite"
              >
                <p className="text-[15px] font-medium text-[#111111]">
                  {FRAMEWORK_NAMES[activeDetection!.detected_framework] ?? activeDetection!.detected_framework}
                </p>
                {activeDetection!.signals.length > 0 && (
                  <p className="text-[12px] font-mono text-[#555555] mt-1">
                    {activeDetection!.signals.join(" · ")}
                  </p>
                )}
                <p className="text-[12px] font-mono font-bold text-[#111111] mt-1">
                  {getPublishPathDisplay(activeDetection!.detected_framework, activeDetection!.publish_path)}
                </p>
                {activeDetection!.confidence === "low" && activeDetection!.detected_framework === "nextjs" && (
                  <div className="mt-3 pt-3 border-t border-[#E5E5E5] space-y-2">
                    <p className="text-[14px] text-[#555555]" style={{ fontFamily: "Inter, sans-serif" }}>
                      Content folder not detected. Confirm your publish path before your first post.
                    </p>
                    <input
                      type="text"
                      value={manualPublishPath}
                      onChange={(e) => setManualPublishPath(e.target.value)}
                      placeholder="e.g. content/blog"
                      className="w-full border-b border-[#111111] outline-none bg-transparent py-2 text-sm text-[#111111] font-mono"
                      aria-label="Custom publish path"
                    />
                    <Button
                      variant="primary"
                      onClick={handleConfirmPublishPath}
                      disabled={frameworkMutation.isPending || !manualPublishPath.trim()}
                    >
                      {frameworkMutation.isPending ? "Saving…" : "Confirm path"}
                    </Button>
                  </div>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button
                    onClick={handleRescan}
                    disabled={detectMutation.isPending}
                    className="px-4 py-1.5 border border-[#111111] bg-transparent text-[#111111] text-xs font-medium hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                    aria-label="Re-scan repository for framework"
                  >
                    Re-scan
                  </button>
                  <button
                    onClick={() => settingsMutation.mutate(!directCommitDefault)}
                    disabled={settingsMutation.isPending}
                    aria-pressed={directCommitDefault}
                    className="px-4 py-1.5 border border-[#555555] bg-transparent text-[#555555] text-xs font-medium hover:border-[#111111] hover:text-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 disabled:opacity-50"
                  >
                    {directCommitDefault ? "Default to direct commit: on" : "Default to direct commit"}
                  </button>
                </div>
              </div>
            ) : isAmbiguous ? (
              /* Ambiguous result — radio-style cards */
              <div aria-live="polite">
                <p className="text-xs font-medium text-[#111111] mb-3">Multiple frameworks detected. Choose one:</p>
                <div className="space-y-2">
                  {activeDetection!.candidates.map((candidate) => {
                    const isSelected = (selectedCandidate ?? activeDetection!.candidates[0].framework) === candidate.framework;
                    return (
                      <button
                        key={candidate.framework}
                        onClick={() => setSelectedCandidate(candidate.framework)}
                        className={`w-full text-left p-3 rounded-none border transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 ${
                          isSelected
                            ? "bg-[#FFF1B8] border-[#111111] shadow-[4px_4px_0px_#111111]"
                            : "bg-white border-[#E5E5E5]"
                        }`}
                        aria-pressed={isSelected}
                        aria-label={`Select ${FRAMEWORK_NAMES[candidate.framework] ?? candidate.framework}`}
                      >
                        <p className="text-sm font-medium text-[#111111]">
                          {FRAMEWORK_NAMES[candidate.framework] ?? candidate.framework}
                        </p>
                        <p className="text-[12px] font-mono text-[#555555] mt-0.5">
                          {getPublishPathDisplay(candidate.framework, candidate.publish_path)}
                        </p>
                      </button>
                    );
                  })}
                </div>
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="primary"
                    onClick={handleConfirmCandidate}
                    disabled={frameworkMutation.isPending}
                  >
                    {frameworkMutation.isPending ? "Saving…" : "Confirm selection"}
                  </Button>
                  <button
                    onClick={handleRescan}
                    disabled={detectMutation.isPending}
                    className="px-4 py-2 border border-[#111111] bg-transparent text-[#111111] text-xs font-medium hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                    aria-label="Re-scan repository"
                  >
                    Re-scan
                  </button>
                </div>
              </div>
            ) : isUnknown ? (
              /* Unknown result — manual dropdown */
              <div aria-live="polite">
                <p className="text-sm text-[#555555] mb-3">
                  Framework not detected. Choose your publish format manually.
                </p>
                <select
                  value={unknownFramework}
                  onChange={(e) => setUnknownFramework(e.target.value)}
                  className="w-full border-b border-[#111111] outline-none bg-transparent py-2 text-sm text-[#111111] mb-3"
                  aria-label="Select blog framework"
                >
                  {SELECTABLE_FRAMEWORKS.map((fw) => (
                    <option key={fw} value={fw}>
                      {FRAMEWORK_NAMES[fw] ?? fw}
                    </option>
                  ))}
                </select>
                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    onClick={handleConfirmUnknown}
                    disabled={frameworkMutation.isPending}
                  >
                    {frameworkMutation.isPending ? "Saving…" : "Save selection"}
                  </Button>
                  <button
                    onClick={handleRescan}
                    disabled={detectMutation.isPending}
                    className="px-4 py-2 border border-[#111111] bg-transparent text-[#111111] text-xs font-medium hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                    aria-label="Re-scan repository"
                  >
                    Re-scan
                  </button>
                </div>
              </div>
            ) : (
              /* No detection yet (page refresh) — prompt to scan */
              <button
                onClick={handleRescan}
                className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
                aria-label="Scan repository for framework"
              >
                Scan repository for framework
              </button>
            )}
          </div>
        )}
      </div>

      <Modal
        isOpen={showDisconnect}
        onClose={() => setShowDisconnect(false)}
        title="Disconnect GitHub?"
        titleId="disconnect-github-dialog-heading"
        triggerRef={disconnectTriggerRef}
      >
        <p className="text-sm text-[#555555] mb-6">
          Future campaigns will not publish to this GitHub repository. The GitHub App installation itself is not revoked.
        </p>
        {disconnectError && (
          <p className="text-xs text-[#C0392B] mb-4" role="alert">{disconnectError}</p>
        )}
        <div className="flex gap-3">
          <Button
            variant="danger"
            onClick={handleDisconnect}
            disabled={disconnecting}
            aria-label="Disconnect GitHub"
          >
            {disconnecting ? "Disconnecting…" : "Disconnect"}
          </Button>
          <Button variant="secondary" onClick={() => setShowDisconnect(false)}>
            Cancel
          </Button>
        </div>
      </Modal>
    </>
  );
}
