---

### File 3: `design.prd.md`

```markdown
# Design System: "Paper Style"

## 1. Aesthetic Vision
The UI should feel like a high-end, minimalist editorial desk. It emphasizes writing and reading. No heavy gradients, no bubbly tech-SaaS shadows. 
**Keywords:** Brutalist, Academic, Notion-esque, Ink & Paper.

## 2. Color Palette
* **Background (Paper):** Off-White / Cream (`#F9F9F6`)
* **Primary Text (Ink):** Deep Black (`#111111`)
* **Secondary Text (Graphite):** Dark Gray (`#555555`)
* **Borders / Dividers:** Light Gray (`#E5E5E5`)
* **Accent (Highlighter):** Pale Yellow (`#FFF1B8`) for emphasizing keywords or active states.
* **Danger/Reject:** Muted Red (`#8B0000`)
* **Success/Approve:** Muted Green (`#2E4F2E`)

## 3. Typography
* **Headings (H1/H2):** Serif. Suggestion: `Playfair Display`, `Merriweather`, or `Georgia`.
* **Body / UI Elements:** Clean Sans-Serif. Suggestion: `Inter`, `Geist`, or `Helvetica Neue`.
* **Brain Dump Input / Code / System Logs:** Monospace. Suggestion: `JetBrains Mono` or `Courier New`.

## 4. Component Styling (Tailwind CSS Directives)
* **Cards & Containers:** Sharp corners (`rounded-none` or `rounded-sm`), 1px solid borders (`border border-black/10`), flat design (no drop shadows, or hard brutalist shadows `shadow-[4px_4px_0px_rgba(0,0,0,1)]`).
* **Buttons:** 
  * *Primary:* Black background, white text, sharp corners, invert on hover.
  * *Secondary:* Transparent background, 1px black border.
* **Inputs:** Transparent backgrounds, bottom border only (`border-b border-black`), no outline ring, monospace font.
* **Animations:** Typewriter effect for AI generation loading states. Fast, snappy transitions.