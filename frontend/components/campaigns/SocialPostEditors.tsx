"use client";

import { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { campaignsApi, APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformIcon } from "@/components/ui/PlatformIcon";

const X_LIMIT = 280;
const LINKEDIN_LIMIT = 1300;
// AC #2: danger at 267 chars (95% of 280, rounded up per spec)
const X_DANGER_THRESHOLD = 267;
// AC #3: danger at 1235 chars (95% of 1300 = 1235.0 exactly)
const LINKEDIN_DANGER_THRESHOLD = 1235;

interface MetaContext {
  threads?: boolean;
  instagram?: boolean;
  facebook_page?: boolean;
}

interface SocialPostEditorsProps {
  campaignId: string;
  initialXPost: string | null;
  initialLinkedInPost: string | null;
  readOnly?: boolean;
  showXSection?: boolean;
  showLinkedInSection?: boolean;
  metaContext?: MetaContext;
}

export interface SocialPostEditorsHandle {
  getCurrentValues: () => { x_post: string; linkedin_post: string };
}

export const SocialPostEditors = forwardRef<
  SocialPostEditorsHandle,
  SocialPostEditorsProps
>(({ campaignId, initialXPost, initialLinkedInPost, readOnly = false, showXSection = true, showLinkedInSection = true, metaContext }, ref) => {
  const [xPost, setXPost] = useState(initialXPost ?? "");
  const [linkedinPost, setLinkedInPost] = useState(initialLinkedInPost ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // Sync state when props arrive post-generation (null → value transition only)
  useEffect(() => {
    if (initialXPost && xPost === "") setXPost(initialXPost);
  }, [initialXPost]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (initialLinkedInPost && linkedinPost === "") setLinkedInPost(initialLinkedInPost);
  }, [initialLinkedInPost]); // eslint-disable-line react-hooks/exhaustive-deps

  const addToast = useUIStore((s) => s.addToast);

  useImperativeHandle(
    ref,
    () => ({ getCurrentValues: () => ({ x_post: xPost, linkedin_post: linkedinPost }) }),
    [xPost, linkedinPost],
  );

  const xCount = xPost.length;
  const xAtDanger = xCount >= X_DANGER_THRESHOLD;

  const liCount = linkedinPost.length;
  const liAtDanger = liCount >= LINKEDIN_DANGER_THRESHOLD;

  async function handleSave() {
    setIsSaving(true);
    try {
      await campaignsApi.patch(campaignId, {
        x_post: xPost,
        linkedin_post: linkedinPost,
      });
      setIsDirty(false);
      addToast("Social posts saved.", "success");
    } catch (err) {
      const message = err instanceof APIError ? err.message : "Failed to save social posts.";
      addToast(message, "error");
    } finally {
      setIsSaving(false);
    }
  }

  const textareaBase =
    "w-full resize-none bg-transparent border-b border-ink focus:border-b-2 focus:outline-none px-0 py-2 text-sm font-mono text-ink placeholder:text-graphite disabled:opacity-60 disabled:cursor-default";

  return (
    <div className="space-y-8">
      {showXSection !== false && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="x-post"
              className="text-xs font-mono uppercase tracking-widest text-graphite"
            >
              X (Twitter)
            </label>
            {metaContext?.threads && (
              <span
                className="flex items-center gap-0.5 text-[10px] font-mono text-graphite"
                aria-label="Also posts to Threads"
              >
                <PlatformIcon platform="threads" className="size-3" color="mono" aria-hidden="true" />
                Threads
              </span>
            )}
          </div>
          <textarea
            id="x-post"
            value={xPost}
            onChange={(e) => {
              setXPost(e.target.value);
              setIsDirty(true);
            }}
            disabled={readOnly}
            rows={4}
            aria-label="X post content"
            aria-describedby={!readOnly ? "x-post-counter" : undefined}
            className={textareaBase}
            placeholder="X post..."
          />
          {!readOnly && (
            <span
              id="x-post-counter"
              className={`text-xs font-mono mt-1 block ${xAtDanger ? "text-danger" : "text-graphite"}`}
              aria-live="polite"
              aria-atomic="true"
            >
              {xCount} / {X_LIMIT}
            </span>
          )}
        </div>
      )}

      {showLinkedInSection !== false && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="linkedin-post"
              className="text-xs font-mono uppercase tracking-widest text-graphite"
            >
              LinkedIn
            </label>
            {(metaContext?.instagram || metaContext?.facebook_page) && (
              <span className="flex items-center gap-1.5 text-[10px] font-mono text-graphite">
                {metaContext.instagram && (
                  <span
                    className="flex items-center gap-0.5"
                    aria-label="Also used as Instagram caption"
                  >
                    <PlatformIcon platform="instagram" className="size-3" color="mono" aria-hidden="true" />
                    Instagram
                  </span>
                )}
                {metaContext.instagram && metaContext.facebook_page && (
                  <span aria-hidden="true" className="text-border">·</span>
                )}
                {metaContext.facebook_page && (
                  <span
                    className="flex items-center gap-0.5"
                    aria-label="Also used as Facebook Page post"
                  >
                    <PlatformIcon platform="facebook_page" className="size-3" color="mono" aria-hidden="true" />
                    Facebook
                  </span>
                )}
              </span>
            )}
          </div>
          <textarea
            id="linkedin-post"
            value={linkedinPost}
            onChange={(e) => {
              setLinkedInPost(e.target.value);
              setIsDirty(true);
            }}
            disabled={readOnly}
            rows={8}
            aria-label="LinkedIn post content"
            aria-describedby={!readOnly ? "linkedin-post-counter" : undefined}
            className={textareaBase}
            placeholder="LinkedIn post..."
          />
          {!readOnly && (
            <span
              id="linkedin-post-counter"
              className={`text-xs font-mono mt-1 block ${liAtDanger ? "text-danger" : "text-graphite"}`}
              aria-live="polite"
              aria-atomic="true"
            >
              {liCount} / {LINKEDIN_LIMIT}
            </span>
          )}
        </div>
      )}

      {/* Save button — only shown when editable and dirty */}
      {!readOnly && isDirty && (
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="inline-flex items-center gap-2 px-4 py-2 border border-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isSaving ? (
            <>
              <span
                className="inline-block w-3 h-3 border border-current border-t-transparent rounded-full animate-spin"
                aria-hidden="true"
              />
              Saving…
            </>
          ) : (
            "Save social posts"
          )}
        </button>
      )}
    </div>
  );
});

SocialPostEditors.displayName = "SocialPostEditors";
