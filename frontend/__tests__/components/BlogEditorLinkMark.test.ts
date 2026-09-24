import { describe, it, expect, afterEach } from "vitest";
import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";

// Real (unmocked) TipTap editor tests for the link-type rewrite fix.
//
// The component test in BlogEditor.test.tsx mocks @tiptap/react, so it can only
// assert that the command chain is dispatched (extendMarkRange -> setLink). These
// tests drive a real Editor so they observe the actual serialised rel/target in
// getHTML() — the value that ends up in the saved blog_html. Without this, a
// regression that keeps extendMarkRange("link") in the chain but stops persisting
// the flipped rel (e.g. a TipTap semantics change) would ship with green mock tests.
// See spec-fix-link-type-toggle-persistence.md.

// Mirrors the extension config in BlogEditor.tsx.
function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [
      StarterKit.configure({
        horizontalRule: false,
        strike: false,
        link: { openOnClick: false, HTMLAttributes: { class: "underline" } },
      }),
    ],
    content,
  });
}

// Place a collapsed cursor inside the link text — the exact interaction that
// motivated the fix (user clicks into a link, no text selected).
function collapseCursorInsideLink(editor: Editor): void {
  editor.commands.setTextSelection(3);
  expect(editor.isActive("link")).toBe(true);
  expect(editor.state.selection.empty).toBe(true);
}

const NOFOLLOW_LINK = '<p><a href="https://x.com" rel="nofollow noopener noreferrer">link text</a></p>';

describe("BlogEditor link-mark rewrite (real editor)", () => {
  let editor: Editor;
  afterEach(() => editor?.destroy());

  it("negative control: setLink WITHOUT extendMarkRange leaves the existing link's rel unchanged on a collapsed cursor", () => {
    editor = makeEditor(NOFOLLOW_LINK);
    collapseCursorInsideLink(editor);
    // Reproduces the bug: setMark on a collapsed selection only sets stored marks.
    editor.chain().setLink({ href: "https://x.com", rel: "noopener noreferrer", target: undefined }).run();
    expect(editor.getHTML()).toContain("nofollow");
  });

  it("extendMarkRange('link') then setLink rewrites the whole link so nofollow is dropped (nofollow -> dofollow)", () => {
    editor = makeEditor(NOFOLLOW_LINK);
    collapseCursorInsideLink(editor);
    editor.chain().extendMarkRange("link").setLink({ href: "https://x.com", rel: "noopener noreferrer", target: undefined }).run();
    const html = editor.getHTML();
    expect(html).not.toContain("nofollow");
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain('href="https://x.com"');
  });

  it("extendMarkRange('link') then setLink adds nofollow + target=_blank (dofollow -> nofollow)", () => {
    editor = makeEditor('<p><a href="https://y.com" rel="noopener noreferrer">link text</a></p>');
    collapseCursorInsideLink(editor);
    editor.chain().extendMarkRange("link").setLink({ href: "https://y.com", rel: "nofollow noopener noreferrer", target: "_blank" }).run();
    const html = editor.getHTML();
    expect(html).toContain("nofollow");
    expect(html).toContain('target="_blank"');
  });

  it("a link with no rel (token-API published) becomes dofollow after the rewrite", () => {
    editor = makeEditor('<p><a href="https://token.example">link text</a></p>');
    collapseCursorInsideLink(editor);
    editor.chain().extendMarkRange("link").setLink({ href: "https://token.example", rel: "noopener noreferrer", target: undefined }).run();
    const html = editor.getHTML();
    expect(html).not.toContain("nofollow");
    expect(html).toContain('rel="noopener noreferrer"');
  });
});
