---
baseline_commit: ca6d60a02263b31544f5aa585fe8dc08ee42be33
---

# Story 11.4: Onboarding Platform Connection Step

Status: done

## Story

As a newly registered user completing onboarding,
I want to connect a publishing platform during setup,
so that my first campaign is ready to publish the moment it's approved — without discovering a dead-end after the fact.

## Acceptance Criteria

1. **Given** a user completes Step 2 (voice setup) of onboarding, **When** they advance (confirm or skip), **Then** they land on new Step 3 "Where will you publish?" with progress indicator "3 of 4"; the brain dump textarea is now Step 4 (progress "4 of 4").

2. **Given** Step 3 renders, **When** the page loads, **Then** it shows: Playfair Display H2 "Where will you publish?" (centered, Ink); Inter 15px Graphite subtext "Connect a platform so you're ready to publish your first campaign in one click." (centered); a vertical list of four `PlatformConnectionCard` components for platforms `["wordpress", "x", "linkedin", "webflow"]` in that order; `github_pages` is NOT shown in onboarding (its setup requires repo selection and framework detection, which is too complex for onboarding); a skip link below the card list: "I'll connect a platform later."

3. **Given** Step 3 renders, **When** a user connects any platform (inline credential form or OAuth), **Then** the `PlatformConnectionCard` updates to "Connected" state (existing card behavior via TanStack Query invalidation); a primary "Continue" button appears below the card list (not present until ≥1 platform is connected); the skip link remains visible so the user can still advance without connecting more.

4. **Given** a user clicks "Continue" on Step 3 after connecting a platform, **Then** they advance to Step 4 (brain dump).

5. **Given** a user clicks "I'll connect a platform later" on Step 3, **Then** they advance to Step 4 (brain dump) without any API call; no platform connection is required.

6. **Given** Step 3 renders for a user who skipped Step 1 (no `createdClientId`), **When** the component detects `createdClientId === null && activeClientId === null`, **Then** it auto-advances to Step 4 immediately without rendering Step 3 UI (platform connection requires a client; skipping Step 1 still allows reaching Step 4 via the existing Step 2 → Step 3 path, but Step 3 is silently skipped).

7. **Given** a user clicks an OAuth "Connect" button (X, LinkedIn, or WordPress.com) on Step 3, **When** the OAuth link is clicked, **Then** `sessionStorage.setItem('onboarding_client_id', createdClientId)` is called first; the OAuth initiation URL includes `&return_to=onboarding` (e.g., `/api/auth/x?client_id={clientId}&return_to=onboarding`).

8. **Given** an OAuth flow initiated from onboarding completes, **When** the Next.js OAuth callback processes the result, **Then** if the `oauth_state_{platform}` cookie contains `returnTo: 'onboarding'`, the callback redirects to `/onboarding?success={platform}` (instead of the usual `/clients/{clientId}/connections?success={platform}`); on error, redirects to `/onboarding?error={encodedMessage}`.

9. **Given** `OnboardingFlow` mounts and `window.location.search` contains `?success={platform}`, **When** `sessionStorage.getItem('onboarding_client_id')` is non-null, **Then** the component restores `createdClientId` from sessionStorage, clears `sessionStorage('onboarding_client_id')`, cleans the URL via `window.history.replaceState`, and auto-advances to Step 4 (the platform is already connected; no need to show Step 3 again); `step2View` should be set to `"questionnaire"` as a safe default (Step 2 state is not preserved).

10. **Given** `OnboardingFlow` mounts and `window.location.search` contains `?error={message}`, **When** `sessionStorage.getItem('onboarding_client_id')` is non-null, **Then** the component restores `createdClientId`, advances to Step 3 (showing the platform step), and passes the error message to `OnboardingPlatformStep` so it can render an error banner; cleans the URL.

11. **Given** progress indicators throughout the flow, **When** they render, **Then** Step 2 shows "2 of 4", Step 3 shows "3 of 4", Step 4 shows "4 of 4"; Step 1 continues to show no progress indicator (existing behavior from AC of Story 2.7).

12. **Given** the existing middleware and `complete-onboarding` flow, **When** the OAuth callback redirects to `/onboarding?success=x`, **Then** the middleware correctly allows this (it already does: `/onboarding` is excluded from the "redirect to /onboarding" rule in middleware.ts:41); no middleware changes are needed.

13. **Given** the four OAuth callback routes (`x`, `linkedin`, `wordpress-com`, `github`), **When** `returnTo` is read from the state cookie, **Then** only `x`, `linkedin`, and `wordpress-com` callbacks are modified (GitHub connection happens outside onboarding; its callback is not touched by this story).

## Tasks / Subtasks

### Task 1: New component — `OnboardingPlatformStep` (AC: 2, 3, 4, 5, 6)

- [x] 1.1 Create `frontend/components/onboarding/OnboardingPlatformStep.tsx` (`'use client'`)
- [x] 1.2 Component signature:
  ```typescript
  interface Props {
    clientId: string;
    oauthError?: string | null; // passed in from OnboardingFlow if ?error= was in URL on mount
    onContinue: () => void;
    onSkip: () => void;
  }
  ```
- [x] 1.3 Use TanStack Query to load connections:
  ```typescript
  const { data: connections } = useQuery({
    queryKey: ["platform-connections", clientId],
    queryFn: () => publishingApi.listConnections(clientId),
    staleTime: 15_000,
  });
  const hasConnection = (connections?.items ?? []).some((c) => c.connected);
  ```
- [x] 1.4 Define `ONBOARDING_PLATFORMS = ["wordpress", "x", "linkedin", "webflow"] as const` — this is the ONLY difference from `PlatformConnectionsClient` (which shows all 5 including `github_pages`)
- [x] 1.5 Render platform cards: filter `connections?.items` to only ONBOARDING_PLATFORMS; fall back to `ONBOARDING_PLATFORMS.map(p => ({ platform: p, connected: false }))` if loading
- [x] 1.6 Render each platform as `<PlatformConnectionCard clientId={clientId} connection={connection} />` — reuse the existing component fully; no new card UI
- [x] 1.7 Wrap cards in `<div className="space-y-4">` (matches `PlatformConnectionsClient` layout)
- [x] 1.8 Show a loading skeleton while connections are loading: `{isLoading && ONBOARDING_PLATFORMS.map(p => <PlatformConnectionCardSkeleton key={p} />)}`
- [x] 1.9 Show `oauthError` banner when prop is non-null:
  ```tsx
  {oauthError && (
    <div role="alert" className="border border-[#8B0000]/30 bg-[#8B0000]/5 p-4 mb-4">
      <p className="text-sm font-mono text-[#8B0000]">{oauthError}</p>
    </div>
  )}
  ```
- [x] 1.10 Show "Continue" primary button only when `hasConnection` is true:
  ```tsx
  {hasConnection && (
    <Button type="button" onClick={onContinue} className="w-full justify-center mt-6">
      Continue
    </Button>
  )}
  ```
- [x] 1.11 Render skip link using existing `SkipLink` component (it's defined inside `OnboardingFlow.tsx` — move it to `frontend/components/onboarding/SkipLink.tsx` OR duplicate the pattern inline)

  **IMPORTANT**: `SkipLink` and `ProgressIndicator` are currently defined as module-level functions inside `OnboardingFlow.tsx`, not exported. Check if they need extraction — see Dev Notes for guidance.

### Task 2: Modify `OnboardingFlow.tsx` — step machine expansion (AC: 1, 6, 9, 10, 11)

- [x] 2.1 Change `OnboardingStep` type: `type OnboardingStep = 1 | 2 | 3 | 4;`
- [x] 2.2 Add Step 3 state variables:
  ```typescript
  const [oauthReturnError, setOauthReturnError] = useState<string | null>(null);
  ```
- [x] 2.3 Add OAuth return detection on mount (runs once):
  ```typescript
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthSuccess = params.get("success");
    const oauthError = params.get("error");
    const savedClientId = sessionStorage.getItem("onboarding_client_id");
    if (!savedClientId) return; // not from OAuth redirect
    // Clean up
    sessionStorage.removeItem("onboarding_client_id");
    window.history.replaceState({}, "", "/onboarding");
    setCreatedClientId(savedClientId);
    setStep2View("questionnaire"); // safe default
    if (oauthSuccess) {
      setStep(4); // connected — skip past step 3
    } else if (oauthError) {
      setOauthReturnError(decodeURIComponent(oauthError));
      setStep(3); // back to platform step with error
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  ```
- [x] 2.4 Save `createdClientId` to sessionStorage in `handleStep1Submit` after client creation:
  ```typescript
  // After: setCreatedClientId(client.id);
  sessionStorage.setItem("onboarding_client_id", client.id);
  ```
- [x] 2.5 Update `handleStep2Complete` and `handleSkipStep2` to `setStep(3)` (unchanged — was already 3, stays 3 which is now the platform step)
- [x] 2.6 Add handlers for Step 3:
  ```typescript
  const handleStep3Continue = () => setStep(4);
  const handleSkipStep3 = () => setStep(4);
  ```
- [x] 2.7 Update Step 2 progress indicator: `<ProgressIndicator step={2} total={4} />`
- [x] 2.8 Add Step 3 render block (after Step 2 block, before Step 3→4 brain dump block):
  ```typescript
  // Guard: if no client, skip platform step
  if (step === 3 && !createdClientId && !activeClientId) {
    setStep(4);
    return null;
  }

  if (step === 3 && (createdClientId || activeClientId)) {
    return (
      <div className="w-full max-w-lg">
        <ProgressIndicator step={3} total={4} />
        <h2 className="font-['Playfair_Display'] text-[1.5rem] font-bold leading-[1.2] tracking-[-0.01em] text-[#111111] mb-3 text-center">
          Where will you publish?
        </h2>
        <p className="text-[0.9375rem] text-[#555555] leading-[1.6] mb-6 text-center">
          Connect a platform so you&apos;re ready to publish your first campaign in one click.
        </p>
        <OnboardingPlatformStep
          clientId={(createdClientId ?? activeClientId)!}
          oauthError={oauthReturnError}
          onContinue={handleStep3Continue}
          onSkip={handleSkipStep3}
        />
      </div>
    );
  }
  ```
- [x] 2.9 Update Step 4 (brain dump) — change `ProgressIndicator` to `step={4} total={4}`; update all handler names if needed (they stay the same: `handleStep3Submit` and `handleSkipStep3` — RENAME these to avoid confusion):
  - Rename `handleStep3Submit` → `handleStep4Submit`
  - Rename `handleSkipStep3` → `handleSkipStep4`
  - Rename `step3Loading` → `step4Loading`
  - Rename `step3Error` → `step4Error`
  - Update `brainDump.length >= MIN_BRAIN_DUMP` guard to use renamed state

  **IMPORTANT**: Be careful with the rename — the skip handler `handleSkipStep3` is currently used for BOTH the "I'll connect later" link on the old Step 3. After this story, `handleSkipStep3` = advance to Step 4 (platform skip) and `handleSkipStep4` = complete onboarding + navigate to dashboard. Do not confuse them.

### Task 3: Modify OAuth initiation routes — add `return_to` support (AC: 7, 8)

For each of the three routes below, the change is identical: read `?return_to` from query params and include in the state cookie.

- [x] 3.1 `frontend/app/api/auth/x/route.ts`:
  ```typescript
  // In GET handler, after reading clientId:
  const returnTo = searchParams.get("return_to") ?? undefined;
  // In cookie construction:
  const cookieValue = JSON.stringify({ state, codeVerifier, clientId, ...(returnTo ? { returnTo } : {}) });
  ```
- [x] 3.2 `frontend/app/api/auth/linkedin/route.ts`:
  ```typescript
  const returnTo = searchParams.get("return_to") ?? undefined;
  const cookieValue = JSON.stringify({ state, clientId, ...(returnTo ? { returnTo } : {}) });
  ```
- [x] 3.3 `frontend/app/api/auth/wordpress-com/route.ts`:
  ```typescript
  const returnTo = searchParams.get("return_to") ?? undefined;
  // Add to cookie value (check the exact cookie structure in this file first)
  ```
- [x] 3.4 DO NOT modify `frontend/app/api/auth/github/route.ts` — GitHub is not included in the onboarding platform list.

### Task 4: Modify OAuth callback routes — redirect to onboarding when returnTo is set (AC: 8, 13)

For each callback route, parse `returnTo` from the state cookie and use it to choose the redirect target.

- [x] 4.1 `frontend/app/api/auth/x/callback/route.ts`:
  ```typescript
  // oauthState type already has: { state, codeVerifier, clientId }
  // Extend with: returnTo?: string
  // After successful connection, before clearCookieRedirect:
  const returnTo = (oauthState as { state: string; codeVerifier: string; clientId: string; returnTo?: string }).returnTo;
  const successUrl = returnTo === "onboarding"
    ? `${APP_URL}/onboarding?success=x`
    : `${connectionsUrl}?success=x`;
  const errorBase = returnTo === "onboarding"
    ? `${APP_URL}/onboarding`
    : connectionsUrl;
  // Update ALL redirect calls to use errorBase for errors and successUrl for success
  ```
  
  **CRITICAL**: There are FOUR `clearCookieRedirect` calls in this callback (user error, CSRF error, backend failure, catch block). ALL of them must use `errorBase` when `returnTo === 'onboarding'`. Update every one.

- [x] 4.2 `frontend/app/api/auth/linkedin/callback/route.ts` — same pattern; check the callback for its exact error redirect structure and update all error redirects to `errorBase`.

- [x] 4.3 `frontend/app/api/auth/wordpress-com/callback/route.ts` — same pattern.

- [x] 4.4 DO NOT modify `frontend/app/api/auth/github/callback/route.ts`.

### Task 5: Add `return_to=onboarding` to OAuth initiation links in `OnboardingPlatformStep` (AC: 7)

The `PlatformConnectionCard` renders OAuth links as `<a href={`/api/auth/${platform}?client_id=${clientId}`}>`. In the onboarding context, we need `return_to=onboarding` appended AND `sessionStorage` set before the redirect.

- [x] 5.1 `PlatformConnectionCard` does not accept a URL override prop. Do NOT modify `PlatformConnectionCard` itself (it is used in non-onboarding contexts where `return_to` must not be appended).

- [x] 5.2 Instead, `OnboardingPlatformStep` must intercept OAuth clicks before the browser follows the `<a>` link. Add an `onClick` wrapper on the container `<div>` surrounding each `PlatformConnectionCard`:
  ```tsx
  <div
    key={connection.platform}
    onClick={(e) => {
      // Intercept OAuth platform link clicks to save clientId before redirect
      const anchor = (e.target as HTMLElement).closest("a[href^='/api/auth/']");
      if (!anchor) return;
      e.preventDefault();
      sessionStorage.setItem("onboarding_client_id", clientId);
      const href = (anchor as HTMLAnchorElement).href;
      const url = new URL(href);
      url.searchParams.set("return_to", "onboarding");
      window.location.href = url.toString();
    }}
  >
    <PlatformConnectionCard clientId={clientId} connection={connection} />
  </div>
  ```
  
  This approach uses event delegation to intercept OAuth anchor clicks without modifying `PlatformConnectionCard`. The click propagation catches any `<a>` with `/api/auth/` href within the card.

  **IMPORTANT**: Non-OAuth cards (WordPress self-hosted, Webflow) use `<button>` elements that POST credentials inline — they do NOT have `/api/auth/` hrefs and are not affected by this intercept. The `closest("a[href^='/api/auth/']")` selector only matches OAuth initiation links.

### Task 6: `SkipLink` — resolve inline definition (AC: 2, 5)

- [x] 6.1 `SkipLink` is currently defined as a module-level function inside `OnboardingFlow.tsx` (not exported). `OnboardingPlatformStep` is a SEPARATE FILE and cannot import it from there.
- [x] 6.2 **Preferred solution**: Extract `SkipLink` to `frontend/components/onboarding/SkipLink.tsx` and update `OnboardingFlow.tsx` to import from there. This is a pure refactor, no behavior change.
- [x] 6.3 Alternatively, `OnboardingPlatformStep` can define its own local skip link using identical markup — this avoids a cross-file extraction but duplicates ~5 lines of JSX.
- [x] 6.4 Recommend option 6.2 (extraction) since `ProgressIndicator` may also be needed in future onboarding steps.

## Dev Notes

### Critical Architecture: PlatformConnectionCard's OAuth links use `<a>` not `<button>`

In `PlatformConnectionCard.tsx:165-172`:
```tsx
<a
  href={`/api/auth/${connection.platform}?client_id=${clientId}`}
  onClick={() => setLoading(true)}
  className="..."
>
  {loading ? "Connecting..." : `Connect ${label}`}
</a>
```

This `<a>` causes a full page navigation. The event delegation approach in Task 5.2 intercepts this, calls `e.preventDefault()`, modifies the URL, and then does `window.location.href = url` — same end result but with `return_to=onboarding` appended and sessionStorage set.

**Do not add `onClick` directly to the `<a>` inside `PlatformConnectionCard`** — the component's own `onClick={() => setLoading(true)}` runs first but that sets local state that will be lost on navigation anyway.

### OAuth State Cookie Types

`frontend/app/api/auth/x/route.ts` line 41:
```typescript
const cookieValue = JSON.stringify({ state, codeVerifier, clientId });
```

After Task 3.1 this becomes:
```typescript
const cookieValue = JSON.stringify({ state, codeVerifier, clientId, ...(returnTo ? { returnTo } : {}) });
```

In the callback, the type assertion must be extended:
```typescript
type XOAuthState = { state: string; codeVerifier: string; clientId: string; returnTo?: string };
oauthState = JSON.parse(cookieRaw) as XOAuthState;
```

Similarly for LinkedIn (`{ state, clientId, returnTo? }`) and WordPress.com (check exact structure in that file).

### SessionStorage Key: `onboarding_client_id`

This key is only set immediately before an OAuth redirect from onboarding Step 3 and cleared immediately after `OnboardingFlow` detects it on remount. It is never set outside the onboarding context. This is distinct from `localStorage` which `useClientStore` uses for `activeClientId` (Story 2.3 note: do not confuse them).

### Middleware: No changes needed

`frontend/middleware.ts` (Story 2.7 implementation) already has:
```typescript
// Path is /onboarding → don't redirect (even if onboarding_completed=false)
// Path is /clients/*/connections → redirect to /onboarding if onboarding_completed=false
```

After OAuth, the callback redirects to `/onboarding?success=x`. The middleware sees path `/onboarding` — it passes through. The `?success=x` query param is just passed along; the OnboardingFlow reads it. No middleware changes.

### Step 3 Guard: Defensive null check

In `OnboardingFlow.tsx`, the Step 3 guard (Task 2.8) uses `setStep(4)` inside a render function. This calls a state setter during render, which is technically a side effect. Use `useEffect` instead:

```typescript
// Better pattern for the guard:
useEffect(() => {
  if (step === 3 && !createdClientId && !activeClientId) {
    setStep(4);
  }
}, [step, createdClientId, activeClientId]);
```

Then the JSX:
```typescript
if (step === 3 && !createdClientId && !activeClientId) return null; // brief flash until effect fires
if (step === 3 && (createdClientId || activeClientId)) { ... }
```

### `PlatformConnectionsClient` vs `OnboardingPlatformStep` differences

| Aspect | `PlatformConnectionsClient` | `OnboardingPlatformStep` |
|---|---|---|
| Platforms shown | All 5 (incl. `github_pages`) | 4 (excl. `github_pages`) |
| H1 heading | Yes ("Platform Connections") | No |
| Client name subtext | Yes | No |
| OAuth toast handling | Yes (useEffect on success/error params) | No (params handled by `OnboardingFlow` parent) |
| "Continue" CTA | No | Yes (appears when connected) |
| Skip link | No | Yes |
| Use case | Full connections page | Onboarding Step 3 only |

Do NOT extract shared logic into a common component — they serve different purposes and the differences are deliberate.

### UX Design Spec — Step 3 (Paper Style, web-uiux-architect compliant)

```
3 of 4          ← Inter 12px uppercase tracked, Graphite

        Where will you publish?
        (Playfair Display H2, 1.5rem, Ink, centered)

   Connect a platform so you're ready to publish
   your first campaign in one click.
   (Inter 15px, Graphite, leading-[1.6], centered)

   [space-y-4 list of PlatformConnectionCards]
   ┌──────────────────────────────────────────┐
   │ [WP] WORDPRESS            Not connected  │
   │                           [Connect]      │
   ├──────────────────────────────────────────┤
   │ [X]  X (TWITTER)          Not connected  │
   │                           [Connect X]    │
   ├──────────────────────────────────────────┤
   │ [LI] LINKEDIN             Not connected  │
   │                           [Connect]      │
   ├──────────────────────────────────────────┤
   │ [WF] WEBFLOW               Not connected │
   │                           [Connect]      │
   └──────────────────────────────────────────┘

   (After connection — e.g. WordPress connected:)
   ┌──────────────────────────────────────────┐
   │ [WP] WORDPRESS            CONNECTED      │
   │                           mysite.com     │
   │                           [Disconnect]   │
   └──────────────────────────────────────────┘
   (other cards remain, "Continue" appears below)

   [   Continue   ]  ← Primary Button, w-full, mt-6
                      only visible when hasConnection

   I'll connect a platform later.  ← SkipLink, always visible
```

The card list renders inside the same `<div>` as the existing Card wrapper in other steps — but NOT inside `<Card>` because `PlatformConnectionCard` has its own border/background. Use a plain `<div>` wrapper. Do not add `<Card>` wrapping around the connection cards.

### Card NOT used for Step 3

Steps 1 and 2 use the `<Card>` wrapper (white bg, 1px border, p-8). Step 3 does NOT use `<Card>` — `PlatformConnectionCard` components already have their own `bg-white border` styling. Wrapping them in `<Card>` would create double borders and incorrect padding.

### Brain Dump Step Variable Renaming

Current Step 3 (brain dump) uses: `step3Loading`, `step3Error`, `handleStep3Submit`, `handleSkipStep3`.

After this story, these move to Step 4. Rename:
- `step3Loading` → `step4Loading`
- `step3Error` → `step4Error`
- `handleStep3Submit` → `handleStep4Submit`
- `handleSkipStep3` (old brain dump skip) → `handleSkipStep4`

New `handleSkipStep3` = advance to Step 4 (platform skip). Note both old and new `handleSkipStep3` advance to the "next step" — but one called `completeOnboarding()` (the old brain dump skip) and the new one just does `setStep(4)`. Be careful not to merge these two behaviors.

### `handleBrainDumpKeyDown` — no change needed

The keyboard handler for the brain dump textarea (`handleBrainDumpKeyDown`) only uses `brainDump.length >= MIN_BRAIN_DUMP` and `handleStep3Submit` (to be renamed `handleStep4Submit`). Otherwise unchanged.

### Testing

No new backend endpoints or schema changes — platform connection APIs (Epic 5) are fully in place.

Frontend unit tests: not required for this story (existing pattern — only backend logic gets unit tests). The OAuth routing is integration-tested manually.

Manual test checklist (should be verified before marking done):
1. Complete Step 1 → Step 2 → Step 3 → see 4 platform cards, "3 of 4" indicator, no H1 heading
2. Click "I'll connect a platform later" → advance to Step 4 "What's on your mind this week?" with "4 of 4"
3. Connect WordPress (self-hosted) inline → "Continue" button appears → click → Step 4
4. Click "Connect X" → sessionStorage is set → redirect to Twitter → after OAuth → lands on `/onboarding?success=x` → auto-advances to Step 4
5. OAuth error scenario: simulate by modifying callback → lands on `/onboarding?error=...` → Step 3 shows error banner, restores client
6. Skip Step 1 ("Skip for now") → complete onboarding → dashboard (Step 3 is not shown) — existing behavior preserved
7. "2 of 4" indicator visible on Step 2

### Project Structure Notes

**New file:**
- `frontend/components/onboarding/OnboardingPlatformStep.tsx`

**Optionally extracted (if going with Task 6.2):**
- `frontend/components/onboarding/SkipLink.tsx`
- `frontend/components/onboarding/ProgressIndicator.tsx`

**Modified files:**
- `frontend/components/onboarding/OnboardingFlow.tsx` — type, state, handlers, steps 3→4 shift
- `frontend/app/api/auth/x/route.ts` — add `return_to` to cookie
- `frontend/app/api/auth/x/callback/route.ts` — redirect to onboarding when `returnTo === 'onboarding'`
- `frontend/app/api/auth/linkedin/route.ts` — same
- `frontend/app/api/auth/linkedin/callback/route.ts` — same
- `frontend/app/api/auth/wordpress-com/route.ts` — same
- `frontend/app/api/auth/wordpress-com/callback/route.ts` — same

**Unchanged:**
- `frontend/components/publishing/PlatformConnectionCard.tsx` — zero changes
- `frontend/components/publishing/PlatformConnectionsClient.tsx` — zero changes
- `frontend/app/api/auth/github/route.ts` — zero changes
- `frontend/app/api/auth/github/callback/route.ts` — zero changes
- `backend/` — zero changes (no new endpoints, no schema changes)
- `frontend/middleware.ts` — zero changes

### References

- `OnboardingFlow.tsx` current implementation: `frontend/components/onboarding/OnboardingFlow.tsx`
- `PlatformConnectionCard` (OAuth `<a>` link pattern): `frontend/components/publishing/PlatformConnectionCard.tsx:165-172`
- `PlatformConnectionsClient` (query key + platform list): `frontend/components/publishing/PlatformConnectionsClient.tsx`
- `PlatformConnectionCardSkeleton`: `frontend/components/publishing/PlatformConnectionCard.tsx:442-457`
- `publishingApi.listConnections`: `frontend/lib/api.ts:166`
- X OAuth initiation: `frontend/app/api/auth/x/route.ts`
- X OAuth callback: `frontend/app/api/auth/x/callback/route.ts`
- LinkedIn OAuth initiation: `frontend/app/api/auth/linkedin/route.ts`
- WordPress.com OAuth initiation: `frontend/app/api/auth/wordpress-com/route.ts`
- SessionStorage `onboarding_client_id` convention: see Story 2.7 Dev Notes (localStorage NOT used for onboarding_completed; this story uses sessionStorage for cross-redirect client persistence only)
- UX onboarding layout rules (Paper background, no sidebar): Story 2.7 AC#9
- `SkipLink` and `ProgressIndicator` current location: `frontend/components/onboarding/OnboardingFlow.tsx:21-40`
- Middleware onboarding exclusion: `frontend/middleware.ts:41,48` (Story 2.7 review note)
- Story 11.2 context: `_bmad-output/implementation-artifacts/11-2-app-ux-campaign-connections-publishing.md` — this story also adds connections discovery in the app (client detail tab); these are complementary improvements, no overlap

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Extracted `SkipLink` and `ProgressIndicator` to separate files in `frontend/components/onboarding/` for reuse by `OnboardingPlatformStep`
- `OnboardingFlow.tsx` expanded from 3 to 4 steps: step 3 is new platform connection step, step 4 is brain dump (was step 3); step 3 variables renamed to step 4 (step3Loading → step4Loading, etc.)
- `OnboardingPlatformStep.tsx` created: renders 4 platform cards (excludes `github_pages`), uses event delegation for OAuth click interception to inject `return_to=onboarding` and save `sessionStorage.onboarding_client_id`, shows Continue button only when connected, always shows skip link
- OAuth initiation routes (x, linkedin, wordpress-com) updated to include optional `returnTo` field in state cookie
- OAuth callback routes (x, linkedin, wordpress-com) updated: when `returnTo === 'onboarding'`, success redirects to `/onboarding?success={platform}` and error redirects to `/onboarding?error={message}`; ALL error redirect paths use `errorBase` (not just success paths)
- `OnboardingFlow` gains OAuth-return detection effect: on mount reads `?success` / `?error` params, restores `createdClientId` from sessionStorage, cleans URL, advances to step 4 (success) or step 3 with error
- Guard effect: if step 3 but no `createdClientId` and no `activeClientId`, auto-advances to step 4 to handle the skip-step-1 case
- Updated `OnboardingFlow.test.tsx`: added TanStack Query mocks (`useQuery`, `useQueryClient`), renamed helper `advanceToStep3` → `advanceToStep4`, updated progress indicator assertions ("2 of 3"→"2 of 4", "3 of 3"→"4 of 4"), fixed pre-existing em-dash regex bug in error message test; all 7 tests pass

### File List

- `frontend/components/onboarding/OnboardingPlatformStep.tsx` (new)
- `frontend/components/onboarding/SkipLink.tsx` (new)
- `frontend/components/onboarding/ProgressIndicator.tsx` (new)
- `frontend/components/onboarding/OnboardingFlow.tsx` (modified)
- `frontend/app/api/auth/x/route.ts` (modified)
- `frontend/app/api/auth/x/callback/route.ts` (modified)
- `frontend/app/api/auth/linkedin/route.ts` (modified)
- `frontend/app/api/auth/linkedin/callback/route.ts` (modified)
- `frontend/app/api/auth/wordpress-com/route.ts` (modified)
- `frontend/app/api/auth/wordpress-com/callback/route.ts` (modified)
- `frontend/__tests__/components/OnboardingFlow.test.tsx` (modified)

### Review Findings

- [x] [Review][Patch] sessionStorage.setItem at Step 1 triggers false OAuth-return detection on any page reload [frontend/components/onboarding/OnboardingFlow.tsx:312]
- [x] [Review][Patch] decodeURIComponent double-decode on already-decoded URLSearchParams error value [frontend/components/onboarding/OnboardingFlow.tsx:273]
- [x] [Review][Patch] isOnboarding computed from unvalidated cookie before CSRF state check [frontend/app/api/auth/linkedin/callback/route.ts:35, frontend/app/api/auth/x/callback/route.ts:35]
- [x] [Review][Patch] WP.com early error with null oauthState redirects to /clients not /onboarding [frontend/app/api/auth/wordpress-com/callback/route.ts:34]
- [x] [Review][Patch] Query error state not consumed in OnboardingPlatformStep — silent failure, no error UI [frontend/components/onboarding/OnboardingPlatformStep.tsx:19]
- [x] [Review][Patch] oauthReturnError not cleared when subsequent OAuth succeeds [frontend/components/onboarding/OnboardingFlow.tsx:270]
- [x] [Review][Patch] Both ?success and ?error present simultaneously — success wins, error silently dropped [frontend/components/onboarding/OnboardingFlow.tsx:270]
- [x] [Review][Patch] WP.com onboarding success param is "wordpress-com" not "wordpress" vs ONBOARDING_PLATFORMS [frontend/app/api/auth/wordpress-com/callback/route.ts:53]
- [x] [Review][Patch] ProgressIndicator has unnecessary "use client" directive [frontend/components/onboarding/ProgressIndicator.tsx:1]
- [x] [Review][Patch] Click handler e.preventDefault() fires before sessionStorage.setItem; throw leaves user stuck [frontend/components/onboarding/OnboardingPlatformStep.tsx:52]
- [x] [Review][Defer] No test coverage for OAuth return-path mount effect [frontend/__tests__/components/OnboardingFlow.test.tsx] — deferred, pre-existing test pattern

## Change Log

- 2026-07-10: Story 11.4 implemented — new onboarding Step 3 platform connection, 4-step flow, OAuth return_to routing, extracted SkipLink/ProgressIndicator components
