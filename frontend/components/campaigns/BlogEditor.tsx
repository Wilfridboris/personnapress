"use client";

import { forwardRef, useImperativeHandle, useState, useEffect, useRef, useCallback } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import type { Config } from "dompurify";
import { Bold, Italic, Heading2, ImagePlus, Link2, Loader2, PenLine, Quote, RotateCcw, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { campaignsApi, imagesApi } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { Modal } from "@/components/ui/Modal";

export interface BlogEditorHandle {
  getCurrentHtml: () => string;
}

interface BlogEditorProps {
  initialHtml: string;
  campaignId: string;
  /** Client ID required for image uploads. */
  clientId: string;
  readOnly?: boolean;
  onSave?: (html: string) => void;
  /** When true, hides the built-in Save button (use with external save handlers). */
  hideSaveButton?: boolean;
}

// Allowed tags/attrs mirror the backend _ALLOWED_TAGS / _ALLOWED_ATTRS in articles.py and campaigns.py
export const _DOMPURIFY_CONFIG: Config = {
  ALLOWED_TAGS: ["h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "a", "br", "blockquote", "code", "pre", "img", "figure", "figcaption"],
  ALLOWED_ATTR: ["href", "title", "rel", "src", "alt", "width", "height"],
  FORBID_ATTR: ["target", "style", "srcset", "onerror", "onload", "onclick"],
};

// ── Image dialog state ────────────────────────────────────────────────────────

type ImageDialogMode = "insert" | "replace" | "edit-alt";

interface ImageDialogState {
  open: boolean;
  mode: ImageDialogMode;
  file: File | null;
  altText: string;
  caption: string;
  isUploading: boolean;
}

const CLOSED_DIALOG: ImageDialogState = {
  open: false,
  mode: "insert",
  file: null,
  altText: "",
  caption: "",
  isUploading: false,
};

const BlogEditor = forwardRef<BlogEditorHandle, BlogEditorProps>(
  ({ initialHtml, campaignId, clientId, readOnly = false, hideSaveButton = false }, ref) => {
    const [isDirty, setIsDirty] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isMounted, setIsMounted] = useState(false);
    const [dialog, setDialog] = useState<ImageDialogState>(CLOSED_DIALOG);
    const addToast = useUIStore((s) => s.addToast);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const fileInputModeRef = useRef<ImageDialogMode>("insert");
    const altInputRef = useRef<HTMLInputElement>(null);
    const confirmBtnRef = useRef<HTMLButtonElement>(null);

    useEffect(() => { setIsMounted(true); }, []);

    const editor = useEditor({
      immediatelyRender: true,
      extensions: [
        StarterKit.configure({
          horizontalRule: false,
          strike: false,
          link: { openOnClick: false, HTMLAttributes: { class: "underline" } },
        }),
        Image.configure({ inline: false, allowBase64: false }),
      ],
      content: initialHtml,
      editable: !readOnly,
      editorProps: {
        attributes: {
          role: "textbox",
          "aria-multiline": "true",
          "aria-label": "Edit blog post content",
          class: cn(
            "prose prose-sm max-w-none",
            "prose-headings:font-display prose-headings:text-ink prose-headings:font-bold",
            "prose-a:text-ink prose-a:underline",
            "prose-strong:text-ink prose-blockquote:border-l-ink prose-blockquote:text-graphite",
            "prose-img:border prose-img:border-border prose-img:my-4",
            "focus:outline-none min-h-[300px] px-6 py-6",
          ),
        },
        handlePaste(_, event) {
          const items = event.clipboardData?.items;
          if (!items) return false;
          const imageItems = Array.from(items).filter((item) => item.type.startsWith("image/"));
          if (imageItems.length === 0) return false;
          event.preventDefault();
          if (imageItems.length > 1) {
            addToast("Only the first image was inserted; paste one at a time.", "info");
          }
          const file = imageItems[0].getAsFile();
          if (file) openImageDialog("insert", file);
          return true;
        },
        handleDrop(_, event) {
          const files = event.dataTransfer?.files;
          if (!files || files.length === 0) return false;
          const file = files[0];
          if (!file || !file.type.startsWith("image/")) return false;
          event.preventDefault();
          if (files.length > 1) {
            addToast("Only the first image was inserted; drop one at a time.", "info");
          }
          openImageDialog("insert", file);
          return true;
        },
      },
      onUpdate: () => {
        setIsDirty(true);
      },
    });

    useImperativeHandle(ref, () => ({
      getCurrentHtml: () => editor?.getHTML() ?? "",
    }));

    // ── Image dialog helpers ───────────────────────────────────────────────────

    const openImageDialog = useCallback((mode: ImageDialogMode, file: File | null = null) => {
      let currentAlt = "";
      if (mode === "edit-alt" && editor) {
        // getAttributes is safe at any cursor position; nodeAt(selection.from) can return null at node boundaries.
        currentAlt = (editor.getAttributes("image").alt as string | undefined) ?? "";
      }
      setDialog({
        open: true,
        mode,
        file,
        altText: currentAlt,
        caption: "",
        isUploading: false,
      });
    }, [editor]);

    const closeDialog = useCallback(() => {
      setDialog(CLOSED_DIALOG);
    }, []);

    const handleImageConfirm = useCallback(async () => {
      if (!editor) return;

      if (dialog.mode === "edit-alt") {
        // Just update alt attribute on the selected node
        editor.chain().focus().updateAttributes("image", { alt: dialog.altText }).run();
        closeDialog();
        return;
      }

      if (!dialog.file) return;

      setDialog((d) => ({ ...d, isUploading: true }));
      try {
        const { url } = await imagesApi.upload(clientId, dialog.file);
        if (dialog.mode === "replace") {
          // Update the currently selected image node
          editor.chain().focus().updateAttributes("image", { src: url, alt: dialog.altText }).run();
        } else {
          // Insert new image (with optional figure+figcaption)
          if (dialog.caption.trim()) {
            editor.chain().focus().insertContent(
              `<figure><img src="${url}" alt="${dialog.altText.replace(/"/g, "&quot;")}"><figcaption>${dialog.caption.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</figcaption></figure>`
            ).run();
          } else {
            editor.chain().focus().setImage({ src: url, alt: dialog.altText }).run();
          }
        }
        closeDialog();
      } catch (err) {
        addToast(err instanceof Error ? err.message : "Image upload failed.", "error");
        closeDialog();
      }
    }, [editor, dialog, clientId, addToast, closeDialog]);

    const handleFilePickerChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      // Reset input so the same file can be picked again
      e.target.value = "";
      // Use the mode captured at button-click time, not re-evaluated here
      openImageDialog(fileInputModeRef.current, file);
    }, [openImageDialog]);

    const handleInsertImageClick = useCallback(() => {
      fileInputModeRef.current = "insert";
      fileInputRef.current?.click();
    }, []);

    const handleReplaceImageClick = useCallback(() => {
      fileInputModeRef.current = "replace";
      fileInputRef.current?.click();
    }, []);

    // ── Save ──────────────────────────────────────────────────────────────────

    async function handleSave() {
      if (!editor || editor.isEmpty) return;
      const html = editor.getHTML();
      if (!html) return;
      setIsSaving(true);
      try {
        const { default: DOMPurify } = await import("dompurify");
        const sanitized = DOMPurify.sanitize(html, _DOMPURIFY_CONFIG);
        await campaignsApi.patch(campaignId, { blog_html: sanitized });
        addToast("Blog post saved.", "success");
        setIsDirty(false);
      } catch (err) {
        addToast(err instanceof Error ? err.message : "Failed to save.", "error");
      } finally {
        setIsSaving(false);
      }
    }

    const isImageActive = editor?.isActive("image") ?? false;

    return (
      <div>
        {/* Hidden file input for image picker */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={handleFilePickerChange}
        />

        {!readOnly && editor && (
          <div
            className="flex items-center gap-1 px-4 py-2 border-b border-border"
            role="toolbar"
            aria-label="Text formatting"
          >
            <button
              type="button"
              aria-label="Toggle bold"
              onClick={() => editor.chain().focus().toggleBold().run()}
              className={cn(
                "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
                editor.isActive("bold") && "bg-highlighter",
              )}
            >
              <Bold size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Toggle italic"
              onClick={() => editor.chain().focus().toggleItalic().run()}
              className={cn(
                "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
                editor.isActive("italic") && "bg-highlighter",
              )}
            >
              <Italic size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Set link"
              onClick={() => {
                const url = window.prompt("URL:");
                if (url) {
                  editor.chain().focus().setLink({ href: url }).run();
                } else {
                  editor.chain().focus().unsetLink().run();
                }
              }}
              className={cn(
                "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
                editor.isActive("link") && "bg-highlighter",
              )}
            >
              <Link2 size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Toggle heading 2"
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              className={cn(
                "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
                editor.isActive("heading", { level: 2 }) && "bg-highlighter",
              )}
            >
              <Heading2 size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Toggle heading 3"
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 3 }).run()
              }
              className={cn(
                "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
                editor.isActive("heading", { level: 3 }) && "bg-highlighter",
              )}
            >
              <span className="text-xs font-bold">H3</span>
            </button>
            <button
              type="button"
              aria-label="Toggle blockquote"
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
              className={cn(
                "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
                editor.isActive("blockquote") && "bg-highlighter",
              )}
            >
              <Quote size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="Undo"
              onClick={() => editor.chain().focus().undo().run()}
              disabled={!editor.can().undo()}
              className="p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink disabled:opacity-40"
            >
              <RotateCcw size={16} aria-hidden="true" />
            </button>

            {/* Image toolbar section */}
            <div className="ml-1 pl-1 border-l border-border flex items-center gap-1">
              <button
                type="button"
                aria-label="Insert image"
                onClick={handleInsertImageClick}
                className={cn(
                  "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
                  isImageActive && "bg-highlighter",
                )}
              >
                <ImagePlus size={16} aria-hidden="true" />
              </button>

              {/* Selected-image actions — only visible when an image node is selected */}
              {isImageActive && (
                <>
                  <button
                    type="button"
                    aria-label="Replace image"
                    onClick={handleReplaceImageClick}
                    className="p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink"
                  >
                    <ImagePlus size={16} aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    aria-label="Edit alt text"
                    onClick={() => openImageDialog("edit-alt", null)}
                    className="p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink"
                  >
                    <PenLine size={16} aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    aria-label="Remove image"
                    onClick={() => editor.chain().focus().deleteSelection().run()}
                    className="p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink"
                  >
                    <Trash2 size={16} aria-hidden="true" />
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        <EditorContent editor={editor} />

        {!readOnly && !hideSaveButton && (
          <div className="px-6 pb-6">
            <button
              type="button"
              onClick={handleSave}
              disabled={!isMounted || isSaving || !isDirty}
              className="mt-4 px-4 py-2 border border-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 disabled:opacity-40 inline-flex items-center gap-2"
            >
              {isSaving && (
                <span className="inline-block size-4 border-2 border-current border-t-transparent rounded-full animate-spin" aria-hidden="true" />
              )}
              Save edits
            </button>
          </div>
        )}

        {/* Image upload / alt-text dialog */}
        <Modal
          isOpen={dialog.open}
          onClose={closeDialog}
          title={
            dialog.mode === "edit-alt"
              ? "Edit alt text"
              : dialog.mode === "replace"
              ? "Replace image"
              : "Insert image"
          }
          initialFocusRef={altInputRef}
        >
          <div className="space-y-4">
            {dialog.mode !== "edit-alt" && dialog.file && (
              <p className="text-sm text-[#555555] font-mono truncate">{dialog.file.name}</p>
            )}

            <div className="space-y-1.5">
              <label htmlFor="image-alt" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                Alt text
              </label>
              <input
                ref={altInputRef}
                id="image-alt"
                type="text"
                value={dialog.altText}
                onChange={(e) => setDialog((d) => ({ ...d, altText: e.target.value }))}
                placeholder="Describes the image for screen readers and search engines."
                className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
              />
              <p className="text-[11px] text-[#999999]">Describes the image for screen readers and search engines.</p>
            </div>

            {dialog.mode === "insert" && (
              <div className="space-y-1.5">
                <label htmlFor="image-caption" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                  Caption <span className="normal-case font-normal text-[#999999]">optional</span>
                </label>
                <input
                  id="image-caption"
                  type="text"
                  value={dialog.caption}
                  onChange={(e) => setDialog((d) => ({ ...d, caption: e.target.value }))}
                  placeholder="Image caption…"
                  className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
                />
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={closeDialog}
                disabled={dialog.isUploading}
                className="px-4 py-2 text-sm font-medium text-[#555555] hover:text-[#111111] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 disabled:opacity-40 min-h-[44px]"
              >
                Cancel
              </button>
              <button
                ref={confirmBtnRef}
                type="button"
                onClick={handleImageConfirm}
                disabled={!dialog.altText.trim() || dialog.isUploading}
                className={cn(
                  "inline-flex items-center gap-2 px-4 py-2 bg-[#111111] text-white text-sm font-medium",
                  "shadow-[4px_4px_0px_0px_#111111] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all",
                  "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
                  "disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed min-h-[44px]",
                )}
              >
                {dialog.isUploading && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
                {dialog.mode === "edit-alt" ? "Update alt text" : dialog.mode === "replace" ? "Replace image" : "Insert image"}
              </button>
            </div>
          </div>
        </Modal>
      </div>
    );
  },
);

BlogEditor.displayName = "BlogEditor";

export { BlogEditor };
