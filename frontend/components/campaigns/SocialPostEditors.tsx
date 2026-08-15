"use client";

import { useState, useEffect, forwardRef, useImperativeHandle } from "react";
import { Info } from "lucide-react";
import { campaignsApi, APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformIcon } from "@/components/ui/PlatformIcon";

const X_LIMIT = 280;
const LINKEDIN_LIMIT = 1500;
const INSTAGRAM_LIMIT = 2200;
const FACEBOOK_LIMIT = 1000;
const THREADS_LIMIT = 500;
// danger at 95%
const X_DANGER_THRESHOLD = 267;
const LINKEDIN_DANGER_THRESHOLD = 1425;
const THREADS_DANGER_THRESHOLD = 475;

interface MetaContext {
  threads?: boolean;
  instagram?: boolean;
  facebook_page?: boolean;
}

interface SocialPostEditorsProps {
  campaignId: string;
  initialXPost: string | null;
  initialLinkedInPost: string | null;
  initialInstagramCaption?: string | null;
  initialFacebookPost?: string | null;
  initialThreadsPost?: string | null;
  readOnly?: boolean;
  showXSection?: boolean;
  showLinkedInSection?: boolean;
  metaContext?: MetaContext;
  imageUrl?: string | null;
}

export interface SocialPostEditorsHandle {
  getCurrentValues: () => {
    x_post: string;
    linkedin_post: string;
    instagram_caption: string;
    facebook_post: string;
    threads_post: string;
  };
}

export const SocialPostEditors = forwardRef<
  SocialPostEditorsHandle,
  SocialPostEditorsProps
>(({
  campaignId,
  initialXPost,
  initialLinkedInPost,
  initialInstagramCaption,
  initialFacebookPost,
  initialThreadsPost,
  readOnly = false,
  showXSection = true,
  showLinkedInSection = true,
  metaContext,
  imageUrl,
}, ref) => {
  const [xPost, setXPost] = useState(initialXPost ?? "");
  const [linkedinPost, setLinkedInPost] = useState(initialLinkedInPost ?? "");
  const [instagramCaption, setInstagramCaption] = useState(initialInstagramCaption ?? "");
  const [facebookPost, setFacebookPost] = useState(initialFacebookPost ?? "");
  const [threadsPost, setThreadsPost] = useState(initialThreadsPost ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // Sync state when props arrive post-generation (null -> value transition only)
  useEffect(() => {
    if (initialXPost && xPost === "") setXPost(initialXPost);
  }, [initialXPost]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (initialLinkedInPost && linkedinPost === "") setLinkedInPost(initialLinkedInPost);
  }, [initialLinkedInPost]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (initialInstagramCaption && instagramCaption === "") setInstagramCaption(initialInstagramCaption);
  }, [initialInstagramCaption]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (initialFacebookPost && facebookPost === "") setFacebookPost(initialFacebookPost);
  }, [initialFacebookPost]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (initialThreadsPost && threadsPost === "") setThreadsPost(initialThreadsPost);
  }, [initialThreadsPost]); // eslint-disable-line react-hooks/exhaustive-deps

  const addToast = useUIStore((s) => s.addToast);

  useImperativeHandle(
    ref,
    () => ({
      getCurrentValues: () => ({
        x_post: xPost,
        linkedin_post: linkedinPost,
        instagram_caption: instagramCaption,
        facebook_post: facebookPost,
        threads_post: threadsPost,
      }),
    }),
    [xPost, linkedinPost, instagramCaption, facebookPost, threadsPost],
  );

  const xCount = xPost.length;
  const xAtDanger = xCount >= X_DANGER_THRESHOLD;

  const liCount = linkedinPost.length;
  const liAtDanger = liCount >= LINKEDIN_DANGER_THRESHOLD;

  const threadsCount = threadsPost.length;
  const threadsAtDanger = threadsCount >= THREADS_DANGER_THRESHOLD;

  // Show new sections based on platform connection state
  const showInstagram = metaContext?.instagram === true;
  const showFacebook = metaContext?.facebook_page === true;
  const showThreads = metaContext?.threads === true;

  async function handleSave() {
    setIsSaving(true);
    try {
      await campaignsApi.patch(campaignId, {
        x_post: xPost,
        linkedin_post: linkedinPost,
        instagram_caption: instagramCaption,
        facebook_post: facebookPost,
        threads_post: threadsPost,
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
      {imageUrl && (
        <div className="border border-border overflow-hidden aspect-video w-full">
          <img
            src={imageUrl}
            alt="Campaign image"
            className="w-full h-full object-cover"
          />
        </div>
      )}
      {showXSection !== false && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="x-post"
              className="text-xs font-mono uppercase tracking-widest text-graphite"
            >
              X (Twitter)
            </label>
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

      {showInstagram && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="instagram-caption"
              className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-widest text-graphite"
            >
              <PlatformIcon platform="instagram" className="size-3" color="mono" aria-hidden="true" />
              Instagram
            </label>
          </div>
          {!imageUrl && (
            <p className="flex items-center gap-1 text-[10px] font-mono text-graphite -mt-1 mb-2">
              <Info className="size-3 shrink-0" aria-hidden="true" />
              Instagram will be skipped at publish - no image attached to this campaign
            </p>
          )}
          <textarea
            id="instagram-caption"
            value={instagramCaption}
            onChange={(e) => {
              setInstagramCaption(e.target.value);
              setIsDirty(true);
            }}
            disabled={readOnly}
            rows={6}
            aria-label="Instagram caption content"
            aria-describedby={!readOnly ? "instagram-caption-counter" : undefined}
            className={textareaBase}
            placeholder="Instagram caption..."
          />
          {!readOnly && (
            <span
              id="instagram-caption-counter"
              className="text-xs font-mono mt-1 block text-graphite"
              aria-live="polite"
              aria-atomic="true"
            >
              {instagramCaption.length} / {INSTAGRAM_LIMIT}
            </span>
          )}
        </div>
      )}

      {showFacebook && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="facebook-post"
              className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-widest text-graphite"
            >
              <PlatformIcon platform="facebook_page" className="size-3" color="mono" aria-hidden="true" />
              Facebook
            </label>
          </div>
          <textarea
            id="facebook-post"
            value={facebookPost}
            onChange={(e) => {
              setFacebookPost(e.target.value);
              setIsDirty(true);
            }}
            disabled={readOnly}
            rows={5}
            aria-label="Facebook post content"
            aria-describedby={!readOnly ? "facebook-post-counter" : undefined}
            className={textareaBase}
            placeholder="Facebook post..."
          />
          {!readOnly && (
            <span
              id="facebook-post-counter"
              className="text-xs font-mono mt-1 block text-graphite"
              aria-live="polite"
              aria-atomic="true"
            >
              {facebookPost.length} / {FACEBOOK_LIMIT}
            </span>
          )}
        </div>
      )}

      {showThreads && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="threads-post"
              className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-widest text-graphite"
            >
              <PlatformIcon platform="threads" className="size-3" color="mono" aria-hidden="true" />
              Threads
            </label>
          </div>
          <textarea
            id="threads-post"
            value={threadsPost}
            onChange={(e) => {
              setThreadsPost(e.target.value);
              setIsDirty(true);
            }}
            disabled={readOnly}
            rows={4}
            aria-label="Threads post content"
            aria-describedby={!readOnly ? "threads-post-counter" : undefined}
            className={textareaBase}
            placeholder="Threads post..."
          />
          {!readOnly && (
            <span
              id="threads-post-counter"
              className={`text-xs font-mono mt-1 block ${threadsAtDanger ? "text-danger" : "text-graphite"}`}
              aria-live="polite"
              aria-atomic="true"
            >
              {threadsCount} / {THREADS_LIMIT}
            </span>
          )}
        </div>
      )}

      {/* Save button -- only shown when editable and dirty */}
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
              Saving...
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
