---
project_name: 'PersonnaPress'
user_name: 'Boris'
date: '2026-07-02'
sections_completed: ['technology_stack']
existing_patterns_found: 0
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

_Documented after discovery phase_

## Critical Implementation Rules

### Next.js 16 + Turbopack: RSC Re-render Loop in Dev Mode

In Turbopack dev mode, some pages trigger repeated RSC re-renders (15–34+ per visit). Root cause is unknown (likely Turbopack HMR internals). The key mitigation rule:

**Never put API calls in server components that could loop.** Instead, move all backend data fetching to TanStack Query in client components.

- **Symptom:** Next.js server log shows the same page route repeated every ~350ms; FastAPI log shows the same endpoint flooded.
- **Bad pattern:** `async function getClientName()` called inside a server component with `cache: "no-store"` — every RSC re-render hits the backend.
- **Fix applied (commits d880dc6, 0d1b5c9 on `connections/page.tsx`):** Server component only reads the session cookie and passes `clientId` to the client component. Client component fetches client name + data via TanStack Query (direct to FastAPI, not through the RSC cycle). Even if RSC re-renders continue, they are instant and harmless.
- **General rule:** Server components should only do session/auth checks. All data fetching goes in client components via TanStack Query.
