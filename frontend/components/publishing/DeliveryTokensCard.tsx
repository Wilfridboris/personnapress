"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Plus, Trash2 } from "lucide-react";
import { deliveryTokensApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useUIStore } from "@/lib/stores/useUIStore";
import type { DeliveryTokenCreateResponse } from "@/lib/types";

interface Props {
  clientId: string;
}

export function DeliveryTokensCard({ clientId }: Props) {
  const queryClient = useQueryClient();
  const addToast = useUIStore((s) => s.addToast);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRevealModal, setShowRevealModal] = useState(false);
  const [newTokenName, setNewTokenName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [revealedToken, setRevealedToken] = useState<DeliveryTokenCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<{ id: string; name: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["delivery-tokens", clientId],
    queryFn: () => deliveryTokensApi.list(clientId),
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => deliveryTokensApi.create(clientId, name),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["delivery-tokens", clientId] });
      setShowCreateModal(false);
      setNewTokenName("");
      setRevealedToken(result);
      setShowRevealModal(true);
      setCopied(false);
    },
    onError: () => {
      addToast("Failed to create token. Please try again.", "error");
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (tokenId: string) => deliveryTokensApi.revoke(clientId, tokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["delivery-tokens", clientId] });
      setRevokeTarget(null);
      addToast("Token revoked.", "success");
    },
    onError: () => {
      addToast("Failed to revoke token. Please try again.", "error");
    },
  });

  function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = newTokenName.trim();
    if (!trimmed) {
      setNameError("Token name is required.");
      return;
    }
    setNameError(null);
    createMutation.mutate(trimmed);
  }

  function handleCopy() {
    if (!revealedToken) return;
    navigator.clipboard.writeText(revealedToken.token).then(() => {
      setCopied(true);
    }).catch(() => {
      addToast("Failed to copy token. Please select and copy it manually.", "error");
    });
  }

  const tokens = data?.items ?? [];

  return (
    <div className="border border-[#111111] rounded-none p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <KeyRound size={16} className="text-[#111111]" />
          <span className="font-medium text-sm text-[#111111]">Delivery API Tokens</span>
        </div>
        <Button
          variant="secondary"
          onClick={() => {
            setNewTokenName("");
            setNameError(null);
            setShowCreateModal(true);
          }}
        >
          <Plus size={14} className="mr-1" />
          New Token
        </Button>
      </div>

      <p className="text-xs text-[#555555] mb-4">
        Use delivery tokens to fetch your published articles from the public API at{" "}
        <code className="bg-[#f5f5f5] px-1">/public/v1/articles</code>.
        Tokens are shown once at creation.
      </p>

      {isLoading ? (
        <div className="space-y-2">
          {[0, 1].map((i) => (
            <div key={i} className="h-9 bg-[#f0f0f0] animate-pulse rounded-none" />
          ))}
        </div>
      ) : tokens.length === 0 ? (
        <p className="text-xs text-[#888888]">No tokens yet. Create one to access your public API.</p>
      ) : (
        <div className="divide-y divide-[#e8e8e8]">
          {tokens.map((token) => (
            <div key={token.id} className="flex items-center justify-between py-2.5">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-[#111111] font-medium truncate max-w-[180px]">
                    {token.name}
                  </span>
                  {token.revoked && (
                    <span className="text-[10px] text-[#cc3300] border border-[#cc3300] px-1 py-0 leading-4">
                      revoked
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-[#888888] mt-0.5">
                  <code>{token.token_prefix}…</code>
                  {token.last_used_at && (
                    <span className="ml-2">
                      last used {new Date(token.last_used_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              {!token.revoked && (
                <button
                  onClick={() => setRevokeTarget({ id: token.id, name: token.name })}
                  className="ml-3 text-[#888888] hover:text-[#cc3300] transition-colors"
                  aria-label={`Revoke token ${token.name}`}
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create token modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="New Delivery Token"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#111111] mb-1">
              Token name
            </label>
            <input
              type="text"
              value={newTokenName}
              onChange={(e) => {
                setNewTokenName(e.target.value);
                if (nameError) setNameError(null);
              }}
              placeholder="e.g. Production website"
              className="w-full border border-[#111111] rounded-none px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#111111]"
              autoFocus
              maxLength={255}
            />
            {nameError && <p className="text-xs text-[#cc3300] mt-1">{nameError}</p>}
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              type="button"
              onClick={() => setShowCreateModal(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating..." : "Create"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Reveal token modal (shown once) */}
      <Modal
        isOpen={showRevealModal}
        onClose={() => {
          if (!copied && !window.confirm("Have you copied the token? You will not be able to see it again.")) return;
          setShowRevealModal(false);
        }}
        title="Token Created"
      >
        <div className="space-y-4">
          <p className="text-sm text-[#555555]">
            Copy this token now. You will not be able to see it again.
          </p>
          <div className="bg-[#f5f5f5] border border-[#e0e0e0] p-3 font-mono text-xs break-all select-all">
            {revealedToken?.token}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowRevealModal(false)}>
              Done
            </Button>
            <Button onClick={handleCopy}>
              {copied ? "Copied!" : "Copy token"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Revoke confirmation modal */}
      <Modal
        isOpen={revokeTarget !== null}
        onClose={() => setRevokeTarget(null)}
        title="Revoke Token"
      >
        <div className="space-y-4">
          <p className="text-sm text-[#555555]">
            Revoke <strong>{revokeTarget?.name}</strong>? Any application using this token will
            immediately lose access. This cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setRevokeTarget(null)} disabled={revokeMutation.isPending}>
              Cancel
            </Button>
            <Button
              onClick={() => revokeTarget && revokeMutation.mutate(revokeTarget.id)}
              disabled={revokeMutation.isPending}
            >
              {revokeMutation.isPending ? "Revoking..." : "Revoke"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
