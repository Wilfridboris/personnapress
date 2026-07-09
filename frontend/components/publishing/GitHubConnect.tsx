"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { GitBranch } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { publishingApi } from "@/lib/api";
import type { PlatformConnectionStatus } from "@/lib/types";

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
  const disconnectTriggerRef = useRef<HTMLButtonElement>(null);

  const isConnectedNoRepo = connection.connected && !connection.account_identifier;

  const { data: reposData, isLoading: reposLoading } = useQuery({
    queryKey: ["github-repos", clientId],
    queryFn: () => publishingApi.listGitHubRepos(clientId),
    enabled: isConnectedNoRepo,
    staleTime: 60_000,
  });

  async function handleSelectRepo(repoFullName: string) {
    setRepoError(null);
    setRepoLoading(true);
    try {
      await publishingApi.selectGitHubRepo(clientId, repoFullName);
      await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
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
    } catch (e: unknown) {
      setDisconnectError(e instanceof Error ? e.message : "Disconnect failed. Please try again.");
    } finally {
      setDisconnecting(false);
    }
  }

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
