"use client";

import { forwardRef, useImperativeHandle, useState, useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import type { Config } from "dompurify";
import { Bold, Italic, Heading2, Link2, Quote, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { campaignsApi } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";

export interface BlogEditorHandle {
  getCurrentHtml: () => string;
}

interface BlogEditorProps {
  initialHtml: string;
  campaignId: string;
  readOnly?: boolean;
  onSave?: (html: string) => void;
}

const _DOMPURIFY_CONFIG: Config = {
  ALLOWED_TAGS: ["h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "a", "br", "blockquote", "code", "pre"],
  ALLOWED_ATTR: ["href", "title", "rel"],
  FORBID_ATTR: ["target"],
};

const BlogEditor = forwardRef<BlogEditorHandle, BlogEditorProps>(
  ({ initialHtml, campaignId, readOnly = false }, ref) => {
    const [isDirty, setIsDirty] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isMounted, setIsMounted] = useState(false);
    const addToast = useUIStore((s) => s.addToast);

    useEffect(() => { setIsMounted(true); }, []);

    const editor = useEditor({
      extensions: [
        StarterKit.configure({ horizontalRule: false, strike: false }),
        Link.configure({ openOnClick: false, HTMLAttributes: { class: "underline" } }),
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
            "focus:outline-none min-h-[300px] px-6 py-6",
          ),
        },
      },
      onUpdate: () => {
        setIsDirty(true);
      },
    });

    useImperativeHandle(ref, () => ({
      getCurrentHtml: () => editor?.getHTML() ?? "",
    }));

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

    return (
      <div>
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
              {/* Heading3 not in all Lucide versions; render text label */}
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
          </div>
        )}

        <EditorContent editor={editor} />

        {!readOnly && (
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
      </div>
    );
  },
);

BlogEditor.displayName = "BlogEditor";

export { BlogEditor };
