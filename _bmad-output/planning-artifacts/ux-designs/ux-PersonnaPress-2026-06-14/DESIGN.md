---
name: PersonnaPress
description: AI content automation platform. Paper Style design system — brutalist, academic, editorial. Raw Tailwind CSS on Next.js App Router. No component library baseline.
status: final
created: 2026-06-14
updated: 2026-06-14
colors:
  paper: '#F9F9F6'
  ink: '#111111'
  graphite: '#555555'
  border: '#E5E5E5'
  highlighter: '#FFF1B8'
  danger: '#8B0000'
  success: '#2E4F2E'
  white: '#FFFFFF'
typography:
  heading:
    fontFamily: 'Playfair Display'
    fontWeight: '700'
    lineHeight: '1.15'
    letterSpacing: '-0.01em'
  heading-sizes:
    h1: '2.25rem'
    h2: '1.5rem'
    h3: '1.125rem'
  body:
    fontFamily: 'Inter'
    fontSize: '0.9375rem'
    fontWeight: '400'
    lineHeight: '1.6'
  label:
    fontFamily: 'Inter'
    fontSize: '0.75rem'
    fontWeight: '500'
    letterSpacing: '0.06em'
    textTransform: 'uppercase'
  mono:
    fontFamily: 'JetBrains Mono'
    fontSize: '0.875rem'
    fontWeight: '400'
    lineHeight: '1.7'
rounded:
  default: '0px'
  badge: '2px'
spacing:
  page-x: '2rem'
  page-x-lg: '3rem'
  sidebar-width: '240px'
  sidebar-width-collapsed: '56px'
  content-max: '720px'
  section: '2rem'
components:
  button-primary:
    background: '{colors.ink}'
    foreground: '{colors.white}'
    radius: '{rounded.default}'
    border: 'none'
    shadow: '4px 4px 0px {colors.ink}'
    hover: 'background {colors.white}, foreground {colors.ink}, border 1px solid {colors.ink}'
    padding: '0.625rem 1.25rem'
  button-secondary:
    background: 'transparent'
    foreground: '{colors.ink}'
    radius: '{rounded.default}'
    border: '1px solid {colors.ink}'
    shadow: 'none'
    hover: 'background {colors.ink}, foreground {colors.white}'
    padding: '0.625rem 1.25rem'
  button-danger:
    background: '{colors.danger}'
    foreground: '{colors.white}'
    radius: '{rounded.default}'
    border: 'none'
    shadow: 'none'
    padding: '0.625rem 1.25rem'
  input:
    background: 'transparent'
    foreground: '{colors.ink}'
    border: 'none'
    border-bottom: '1px solid {colors.ink}'
    border-bottom-focus: '2px solid {colors.ink}'
    radius: '{rounded.default}'
    fontFamily: '{typography.body.fontFamily}'
    outline: 'none'
    padding: '0.5rem 0'
  brain-dump-input:
    background: 'transparent'
    foreground: '{colors.ink}'
    border: 'none'
    border-bottom: '1px solid {colors.border}'
    border-bottom-focus: '1px solid {colors.ink}'
    radius: '{rounded.default}'
    fontFamily: '{typography.mono.fontFamily}'
    fontSize: '{typography.mono.fontSize}'
    lineHeight: '{typography.mono.lineHeight}'
    outline: 'none'
    resize: 'none'
    minHeight: '120px'
  card:
    background: '{colors.white}'
    border: '1px solid {colors.border}'
    radius: '{rounded.default}'
    shadow: 'none'
    hover-shadow: '4px 4px 0px {colors.ink}'
  card-active:
    background: '{colors.highlighter}'
    border: '1px solid {colors.ink}'
    radius: '{rounded.default}'
    shadow: '4px 4px 0px {colors.ink}'
  status-badge-pending:
    background: '{colors.highlighter}'
    foreground: '{colors.ink}'
    radius: '{rounded.badge}'
    border: '1px solid {colors.ink}'
    fontFamily: '{typography.label.fontFamily}'
    fontSize: '{typography.label.fontSize}'
  status-badge-approved:
    background: '{colors.border}'
    foreground: '{colors.graphite}'
    radius: '{rounded.badge}'
    border: 'none'
  status-badge-published:
    background: '{colors.success}'
    foreground: '{colors.white}'
    radius: '{rounded.badge}'
    border: 'none'
  status-badge-rejected:
    background: 'transparent'
    foreground: '{colors.graphite}'
    radius: '{rounded.badge}'
    border: '1px solid {colors.border}'
    textDecoration: 'line-through'
  status-badge-failed:
    background: '{colors.danger}'
    foreground: '{colors.white}'
    radius: '{rounded.badge}'
    border: 'none'
  sidebar:
    background: '{colors.paper}'
    border-right: '1px solid {colors.border}'
    width: '{spacing.sidebar-width}'
  nav-item:
    background: 'transparent'
    foreground: '{colors.graphite}'
    radius: '{rounded.default}'
    padding: '0.5rem 0.75rem'
    hover: 'background {colors.highlighter}, foreground {colors.ink}'
  nav-item-active:
    background: '{colors.highlighter}'
    foreground: '{colors.ink}'
    border-left: '2px solid {colors.ink}'
  voice-score-warning:
    foreground: '{colors.danger}'
    fontFamily: '{typography.label.fontFamily}'
    fontSize: '{typography.label.fontSize}'
    letterSpacing: '{typography.label.letterSpacing}'
  upgrade-banner:
    background: '{colors.ink}'
    foreground: '{colors.white}'
    padding: '0.625rem {spacing.page-x}'
---

## Brand & Style

PersonnaPress is an AI content automation platform that writes in your voice — not generic AI output, but prose that sounds unmistakably like you. It serves content-driven founders, coaches, and small agencies who need to publish weekly without spending half a day writing.

The brand expression is **editorial authority**. The product handles a serious workflow — writing, publishing, brand representation — and its interface should feel like the tool of a careful craftsperson, not a bubbly SaaS dashboard. The design system is called "Paper Style": off-white ground like a quality notebook page, deep black ink, serif headings that carry editorial weight, monospace type for raw input, and brutalist sharp edges everywhere.

Anti-references: no gradient fills, no rounded pill buttons, no drop shadows with blur, no color-saturated UI chrome, no exclamation marks, no emoji in product copy, no "supercharge your content" energy. Think Notion's restraint crossed with a literary magazine layout.

The typewriter animation for AI generation is the one moment of character — it makes the machine's work visible and builds trust through paced reveal. Everything else is calm, considered, and fast.

## Colors

The palette has one ground, one ink, one accent, and two semantic signals — nothing more.

- **Paper (`#F9F9F6`)** is the page. It is the application background, sidebar background, and default card background. It is warm white, not pure white — the difference reads at a glance as intentional, not default.
- **Ink (`#111111`)** is text, active borders, primary buttons, and hard offset shadows. Near-black, not pure black — preserves Paper's warmth contrast without going stark.
- **Graphite (`#555555`)** is secondary text, inactive nav labels, and subdued metadata (timestamps, character counts). Never used for interactive elements that require discovery.
- **Border (`#E5E5E5`)** is structural dividers: card borders in default state, table rules, section separators, input borders in unfocused state. Not used for type.
- **Highlighter (`#FFF1B8`)** is the accent. Pale yellow, the color of a physical highlighter marker. Used for: active nav items, pending-approval status badges, the active card-hover state, keyboard focus rings on components that can't use a border-bottom focus. One accent, one role — do not repurpose for success or decorative use.
- **Danger (`#8B0000`)** is muted red for destructive actions (Delete client, Reject campaign, error states, voice fidelity warning badge). Never used decoratively.
- **Success (`#2E4F2E`)** is muted green for Approved and Published states. Never used decoratively.
- **White (`#FFFFFF`)** is button foreground text, content areas in Approval Gate blog preview (renders against Paper for contrast), and modal overlays.

Color discipline: if a use case doesn't fit one of these seven roles, there is no eighth color — redesign the element to fit the existing vocabulary.

## Typography

Three roles, three families. Each has one job and does not substitute for another.

**Playfair Display (Headings)** — the editorial serif. Used for H1 (page titles, hero statements) and H2 (section headers within pages). Weight 700. Letter-spacing tight (-0.01em) to read as press-set. The product's one concession to personality — everything else is workhorse type.

**Inter (Body / UI)** — the workmanlike sans-serif. Body copy, labels, button text, metadata, nav items, form labels, character counts, error messages. 15px body, 12px label (uppercased, tracked at 0.06em for legibility as a "category" signal). Line height 1.6 for prose readability in approval previews.

**JetBrains Mono (Monospace)** — for user-generated raw text only. The Brain Dump input, system log displays, generation status messages, and any displayed "raw" content. 14px, line height 1.7. Signals "this is input / this is machine" — visually distinct from all editorial and UI type.

Type scale is restrained: H1 at 2.25rem, H2 at 1.5rem, H3 at 1.125rem, body at 0.9375rem (15px). No H4 — if a section needs a fourth level of heading, redesign the structure.

## Layout & Spacing

Desktop-first responsive web. Left sidebar, persistent at ≥1024px. Primary content width capped at 720px (`{spacing.content-max}`) within the content pane — this is a writing-and-reading product, not a data-grid product. Forcing one-column prose reads as intentional; wide layouts read as distraction.

Page horizontal padding: `{spacing.page-x}` (32px) on tablet, `{spacing.page-x-lg}` (48px) on desktop. Consistent gutter prevents content from appearing to float. Section rhythm uses `{spacing.section}` (32px) vertical gaps between major page sections.

The sidebar is `{spacing.sidebar-width}` (240px) wide on desktop, icon-only at `{spacing.sidebar-width-collapsed}` (56px) on 768–1023px, and a slide-in drawer triggered from a top bar on <768px.

Alignment is strict left-aligned for prose content. No centered body text. No centered headings except on empty states and the onboarding welcome screen.

## Elevation & Depth

Flat surface with one depth signal: the **hard brutalist shadow** (`4px 4px 0px {colors.ink}`). No blur, no spread, no opacity. This shadow appears on:

- Primary buttons (resting state)
- Hovering over interactive campaign cards
- The active card-active component variant

Nothing else has elevation. No layered shadows, no blur-backdrop, no card hover lifts. The hard shadow is a spatial signal ("this moves"), not a decoration.

## Shapes

Sharp everywhere. `rounded-none` for all cards, buttons, input fields, modals, and dialogs. `{rounded.badge}` (2px) for status badges and pills only — the 2px prevents status text from appearing to bleed outside the badge at small sizes, but reads as near-square at a glance.

No pill shapes. No circular icon buttons. No full-radius anything except generated image thumbnails (which are media assets, not UI chrome, and may inherit their own aspect ratio).

## Components

### Buttons

**Primary (`{components.button-primary}`)** — black fill, white text, hard 4px shadow. Inverts on hover (white fill, black text, black border). Used for: "New Campaign," "Approve," "Publish," "Save," "Submit." One primary button per page/modal.

**Secondary (`{components.button-secondary}`)** — white fill, 1px black border, no shadow. Inverts on hover. Used for: "Cancel," "Edit," "Retry," secondary actions that appear alongside a primary.

**Danger (`{components.button-danger}`)** — danger-red fill, white text. Used for: "Reject Campaign," "Delete Client," "Disconnect platform." Always appears inside a confirmation dialog, never as a page-level CTA.

### Inputs

**Standard (`{components.input}`)** — bottom-border only. The border bottom thickens to 2px on focus; there is no ring, outline, or background change. Placeholder text in Graphite. Used for all standard form fields (Client name, website URL, credentials).

**Brain Dump (`{components.brain-dump-input}`)** — the core input. JetBrains Mono, auto-expanding textarea, minimal bottom border that visually recedes so the writing is foreground. The field should disappear as a form element and feel like a blank page. Focus border thickens but stays understated.

### Cards

**Default (`{components.card}`)** — white fill, 1px border, no shadow. Used for Campaign list rows. Hover applies the hard shadow to signal clickability.

**Active (`{components.card-active}`)** — Highlighter fill, 1px ink border, hard shadow. Used for the currently selected/active campaign or the "pending approval" state that requires action.

### Status Badges

Five states per the Campaign lifecycle. Each badge is a small inline pill (2px radius) carrying the label in upper-tracked Inter label type.

- **Pending Approval** — Highlighter fill, ink border. Signals "action required."
- **Approved** — Border fill, Graphite text. Neutral/waiting.
- **Published** — Success green fill, white text. Terminal success state.
- **Rejected** — Transparent fill, border, strikethrough text. Terminal decline state — content will not publish.
- **Failed** — Danger red fill, white text. Requires user action (retry).

### Sidebar & Navigation

**Sidebar (`{components.sidebar}`)** — Paper background, 1px right border. No shadow. Client switcher occupies the top 56px of the sidebar. Below: primary nav links. Below: account/subscription link pinned to bottom.

**Nav item default (`{components.nav-item}`)** — Graphite label. Hover: Highlighter background, Ink text.

**Nav item active (`{components.nav-item-active}`)** — Highlighter background, Ink text, 2px left border in Ink (the tab-stop indicator).

### Specialized Components

**Voice score warning (`{components.voice-score-warning}`)** — Inline in Approval Gate header. Danger-colored, label-size Inter, uppercase-tracked. "VOICE MATCH: 6/10 — REVIEW TONE." Advisory display only.

**Upgrade banner (`{components.upgrade-banner}`)** — Full-width sticky bar at the top of the viewport. Black fill, white text. Non-dismissible. Contains trial status text and "Subscribe" secondary-style CTA (white-on-black border button inverts the secondary style).

**Typewriter loading state** — During AI generation (blog, social, image), the primary content area shows a typewriter animation: text appears character-by-character in JetBrains Mono on a Paper background. Status messages cycle in monospace below the animation ("Analyzing voice profile... Drafting blog post... Checking voice fidelity..."). The animation conveys the machine is doing real work, not a spinner.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Use Playfair Display for H1/H2 only | Set UI labels or body copy in serif |
| Hard 4px offset shadow on primary button and hovering cards | Soft blur-radius shadows anywhere |
| Bottom-border-only on all inputs | Box-border or rounded-corner inputs |
| `rounded-none` on cards, buttons, modals | Rounded-md or pill shapes on interactive elements |
| Status badge colors for Campaign states only | Reuse Highlighter, Danger, or Success for decoration |
| Typewriter animation for AI generation states only | Use typewriter for loading states unrelated to generation |
| One primary button per page context | Multiple primary buttons competing on the same surface |
| Calm, direct copy — "Your draft is ready" | Enthusiasm markers — "Your draft is ready!" |
| Monospace for Brain Dump input and raw system output | Monospace for UI labels or headings |
| Hard left-align prose content | Center body text |
