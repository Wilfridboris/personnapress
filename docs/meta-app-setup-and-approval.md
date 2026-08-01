# Meta App Setup and App Review Guide

This guide covers creating a Meta Business App on the Meta for Developers portal, configuring it for PersonnaPress, and submitting it for App Review so production users can connect Instagram, Facebook Page, and Threads.

---

## Table of Contents

1. [Create the Meta App](#1-create-the-meta-app)
2. [Fill Out Basic & Advanced Settings](#2-fill-out-basic--advanced-settings)
3. [Configure OAuth Redirect URIs](#3-configure-oauth-redirect-uris)
4. [Add Required Products](#4-add-required-products)
5. [Set Environment Variables](#5-set-environment-variables)
6. [Set Up Test Accounts & Test in Development Mode](#6-set-up-test-accounts--test-in-development-mode)
7. [Submit for App Review](#7-submit-for-app-review)
8. [After Approval](#8-after-approval)
9. [Troubleshooting](#troubleshooting)

---

## 1. Create the Meta App

1. Go to [developers.facebook.com/apps](https://developers.facebook.com/apps) and sign in with a Facebook account that has admin access to a Meta Business Portfolio.

2. Click **My Apps** in the top right corner, then click **Create App**.

3. Select your app type. For social publishing select **Business** (supports Pages and Instagram Graph API). Click **Next**.

4. Fill in the app details:
   - **App name**: `PersonnaPress`
   - **App contact email**: your team email address
   - **Business portfolio**: select your business from the dropdown (required for advanced permissions)

5. Click **Create app**. You now have a new app in **Development mode**.

6. From **App Settings > Basic**, copy:
   - **App ID**
   - **App Secret** (click "Show" and verify with your password)

---

## 2. Fill Out Basic & Advanced Settings

Before requesting any permissions, complete the app's foundation in **App Settings > Basic**. Incomplete fields trigger automatic rejection.

| Field | Required value |
|-------|---------------|
| **App Domains** | `personnapress.com` — live, publicly accessible URL only (no localhost, no staging URLs) |
| **Privacy Policy URL** | `https://personnapress.com/privacy` — must be live and explicitly state how user data is handled |
| **Terms of Service URL** | `https://personnapress.com/terms` — must be live |
| **User Data Deletion URL** | A callback URL or page with clear instructions for users to delete their data (missing/broken links cause automatic rejection) |
| **App Icon** | 1024×1024 PNG with transparent background |
| **Category** | Business and Pages (or Utility) |

---

## 3. Configure OAuth Redirect URIs

1. From the left sidebar, click **Facebook Login for Business > Settings** (add the product first if not listed — see Section 4).

2. Under **Valid OAuth Redirect URIs** add:

   | Environment | URI |
   |-------------|-----|
   | Local dev | `http://localhost:3000/api/auth/meta/callback` |
   | Staging | `https://staging.personnapress.com/api/auth/meta/callback` |
   | Production | `https://personnapress.com/api/auth/meta/callback` |

3. Enable **Client OAuth Login** and **Web OAuth Login**. Ensure **Enforce HTTPS** is on.

4. Click **Save changes**.

---

## 4. Add Required Products

PersonnaPress uses two separate tracks: **Facebook Login for Business** for Facebook Page and Instagram, and a **dedicated Threads use case** for Threads. These are configured independently in the Meta dashboard.

### 4a. Facebook Login for Business (Facebook Page + Instagram)

1. From the left sidebar click **Add Product**.
2. Find **Facebook Login for Business** and click **Set up**.
3. Choose **Web** as the platform.
4. Enter your site URL (`https://personnapress.com`) and click **Save**.

### 4b. Instagram (if not automatically added)

1. From **Add Product**, find **Instagram** and click **Set up**.
2. No additional configuration is needed here; permissions are requested at the OAuth step.

### 4c. Threads (dedicated use case)

Threads is treated as a distinct **Threads use case** with its own tester management and review path.

1. From **Add Product** (or **Add use case** depending on your dashboard view), find **Threads** and click **Set up**.
2. Under the Threads use case settings, add **Threads Testers** separately from your app's Facebook Testers (see Section 6).
3. Configure `threads_basic` and `threads_content_publish` under the Threads use case — not under the Facebook Login for Business flow.

> **Implementation note:** Threads publishing endpoints use a completely different base host from Instagram and Facebook. All Threads API calls go to `https://graph.threads.com/v1.0` — not `https://graph.facebook.com`. Using the wrong host will return errors.

---

## 5. Set Environment Variables

Add the following to your environment files. The App ID is public; the App Secret must never be committed to source control.

**`backend/.env`**

```
# Meta Business App (Instagram, Facebook Page, Threads publishing)
META_APP_ID=<your App ID from App Settings > Basic>
META_APP_SECRET=<your App Secret from App Settings > Basic>
```

**`frontend/.env.local`**

```
# Set to true to enable the Meta Platforms connect button in the UI
NEXT_PUBLIC_META_PUBLISHING_ENABLED=true
NEXT_PUBLIC_META_APP_ID=<same App ID>
```

When `NEXT_PUBLIC_META_PUBLISHING_ENABLED` is `false` (the default), the Meta Platforms section in the Connections UI shows a locked "coming soon" state. Keep it `false` in production until App Review is approved.

---

## 6. Set Up Test Accounts & Test in Development Mode

### 6a. Required Test Assets

You cannot submit for review without first successfully using the APIs in Development Mode. Set up:

- A **Facebook account** that administers at least one **Facebook Page**, with a connected **Instagram Business or Creator account** (in Instagram: switch to Professional > Business, then link to the Facebook Page).
- A **Threads profile** linked to the same Instagram account for Threads testing.
- All **media you plan to use for testing** must be hosted on publicly accessible URLs — no gated S3 buckets or local files, as Meta's servers download them at publish time.

### 6b. Add Test Users

**Facebook/Instagram testers:**

1. Go to **Roles > Roles** in the left sidebar.
2. Under **Testers**, click **Add Testers** and enter Facebook usernames or profile URLs.
3. Testers must accept the invitation from their Facebook notifications.

**Threads testers (separate step):**

Threads has its own tester management, independent of app Facebook Roles. Under the Threads use case settings, add Threads testers using their Threads or Instagram usernames. They will receive a separate invite to accept.

### 6c. Scopes

**Facebook/Instagram OAuth flow:**

| Scope | What it grants | PersonnaPress usage |
|-------|---------------|---------------------|
| `pages_show_list` | List of Pages the user administers | Display Page selector at connection time |
| `pages_read_engagement` | Page content, followers data, profile picture, metadata, and insights | Read Page name and ID only; no engagement analytics accessed |
| `pages_manage_posts` | Create, edit, and delete Page posts | Publish campaign text/image to `/{page_id}/feed` |
| `instagram_basic` | Instagram profile info and the user's posted media/text | Read account ID and username only |
| `instagram_content_publish` | Publish media to Instagram as feed posts | Publish campaign images via the media container flow |

**Threads OAuth flow (separate — `https://threads.net/oauth/authorize`):**

`threads_basic` and `threads_content_publish` are only valid through the Threads-specific OAuth, not through Facebook Login. They must NOT be included in the Facebook Login scope string or the OAuth dialog will reject them for developer accounts.

| Scope | What it grants | PersonnaPress usage |
|-------|---------------|---------------------|
| `threads_basic` | Threads profile info and the user's posted media/text content | Read Threads user ID and username only |
| `threads_content_publish` | Publish text and media posts to Threads | Publish campaign short-form text via the Threads container flow |

### 6c-ii. Publishing Rate Limits

Keep these limits in mind when testing and when writing Use Case descriptions. Exceeding them during testing will cause publish calls to fail with 429 errors.

| Platform | Limit | Window | Notes |
|----------|-------|--------|-------|
| Instagram | 100 posts | 24-hour rolling | Carousels count as 1 post |
| Facebook Page | No hard publish limit | — | Enforced by spam signals, not a fixed quota |
| Threads | 250 posts | 24-hour rolling | Carousels count as 1 post |

### 6d. Test the Full Flow Locally

1. Start the backend (`uvicorn`) and frontend (`next dev`).
2. Navigate to `/clients/<id>/connections`.
3. Click **Connect Meta Platforms**.
4. Complete the Facebook login and Page/account selection.
5. On success you should see Instagram, Facebook Page, and Threads listed as connected with the account identifier shown on each card.

**Meta requires at least one successful API call per requested permission in the 30 days prior to submission.** Make sure you successfully publish a post to Facebook, Instagram, and Threads and verify the posts actually appear live on those test accounts.

---

## 7. Submit for App Review

App Review is required before users outside your developer team can connect their accounts. Meta currently takes **approximately 20 days** to review a submission. Plan accordingly before your target launch date.

### 7a. Pre-Submission Technical Gate

Tick every box before pressing record or submitting. A single miss restarts the review clock (2–7 business days per attempt, compounding).

| # | Check | Why it matters |
|---|-------|----------------|
| ☐ | **Live, publicly accessible app URL** — not localhost, not a staging URL behind VPN/IP allowlist | Reviewer must be able to open and test the app |
| ☐ | **Working test credentials provided** in the submission (test user email/password, plus any 2FA bypass) | If the reviewer can't log in, the entire submission is rejected |
| ☐ | **Test user in Development Mode** can complete the full flow exactly as a real user would | Reviewer replicates your described flow with a Development Mode test user |
| ☐ | **Media hosted on publicly accessible URLs** (no auth-gated S3 presigned links that expire, no CDN behind tokens) | Threads/Instagram download media at publish time; gated media fails silently and the demo breaks |
| ☐ | **At least one successful API call** made with each requested permission in the last 30 days | Meta checks call history; zero calls = auto-flag |
| ☐ | **Privacy Policy URL live** (not 404, not a parked domain) | Mandatory field |
| ☐ | **Data Deletion Request callback or instructions URL** working | Non-negotiable; broken links are a documented rejection cause |
| ☐ | **Only the three publishing permissions requested** — do NOT request `threads_manage_replies`, `threads_manage_insights`, `instagram_manage_comments`, or `ads_management` unless you genuinely use them | Over-scoping is a named rejection trigger |
| ☐ | **No placeholder/test content** visible ("lorem ipsum", "test123", fake usernames) | Triggers the "generic/staged screencast" rejection |
| ☐ | **Real Page name and real IG/Threads username** visible throughout | Staged-looking UIs fail the authenticity check |
| ☐ | **Token refresh implemented** (long-lived tokens = 60 days; public-profile grants = 90 days) | Silent access loss looks like broken functionality |
| ☐ | **Screencast recorded fresh** for this submission (not recycled from a previous app or older UI) | Recycled videos are flagged |
| ☐ | **Use Case descriptions NOT finalized until screencast is complete** — the two must match exactly and neither can be edited after submission | Described flow != recorded flow = rejection |
| ☐ | **Business Verification complete** in Meta Business Manager | Required before Advanced Access is granted |

### 7b. Record Screencasts

Meta requires a screencast for each requested permission. Record one continuous take (or three permission-specific segments). Reviewers watch the recordings step by step to verify each permission actively works in your app.

**Format requirements:**

| # | Requirement |
|---|-------------|
| ☐ | **Duration:** 90 seconds – 3 minutes per permission segment |
| ☐ | **Single continuous take** per permission — no cuts, no speed-ups, no jump edits |
| ☐ | **Full browser window visible** — address bar showing your real URL |
| ☐ | **Cursor visible** and moving deliberately; pause 1–2 seconds on each key screen |
| ☐ | **No narration required** but optional on-screen captions help |
| ☐ | **No background music, no fast-forwarding** through the publish step |
| ☐ | **Same test user account** used for all three permission segments |
| ☐ | **1080p minimum**, MP4/MOV |

#### Segment A — Universal Entry (record once, applies to all three permissions)

| Screen | Action | What the reviewer must see |
|--------|--------|---------------------------|
| A1 | App landing/login page | Real production URL in address bar; branded login screen |
| A2 | Login with test credentials | Type the provided test user credentials; successful authentication into the app dashboard |
| **A3** | "Connect Meta Account" screen | A clearly labeled button/screen that initiates the OAuth flow to Meta — this is the entry point reviewers hunt for first |
| **A4** | Meta OAuth dialog — permission grant screen | The Meta-hosted consent dialog showing the EXACT scopes being requested. **Do not skip or fast-forward this screen.** |
| A5 | Successful connection confirmation | UI inside YOUR app confirming the account is linked: connected Page name, IG username (@handle), and Threads handle displayed |

> If A4 is skipped, the reviewer cannot verify the permission was actually granted — instant "unable to verify use case" rejection.

#### Segment B — `pages_manage_posts` (Facebook Page publishing)

| Screen | Action | What the reviewer must see |
|--------|--------|---------------------------|
| B1 | Post composer screen | A compose UI with text field, optional media upload, and a destination selector showing the connected Facebook Page by name |
| B2 | Page selected as publish target | The Facebook Page name clearly highlighted/selected |
| B3 | Content entered | Realistic post text typed, optionally one image attached |
| **B4** | "Publish" button clicked | The exact button that triggers the `POST /{page-id}/feed` call. Button label must match the wording in your Use Case description |
| **B5** | In-app success confirmation | Toast/banner in YOUR UI: "Post published successfully to Facebook" + a link or post ID |
| **B6** | Verify on Facebook | Navigate to the live Facebook Page feed and show the post appearing at the top with the exact same text |

> Skipping B6 is the #1 cause of "screencast doesn't show permission in action."

#### Segment C — `instagram_content_publish` (Instagram publishing)

| Screen | Action | What the reviewer must see |
|--------|--------|---------------------------|
| C1 | Post composer screen | Destination selector showing the connected Instagram Business/Creator account by @username |
| C2 | IG account selected as publish target | @username clearly visible and selected |
| C3 | Media + caption entered | One image or short video from publicly accessible URL, realistic caption typed |
| **C4** | "Publish to Instagram" button clicked | Triggers the two-step flow: container creation then publish |
| **C5** | In-app publishing status / success message | "Publishing..." then "Published to Instagram successfully" in YOUR UI |
| **C6** | Verify on Instagram | Open instagram.com logged in as the same @username; show the new post at the top of the profile grid |

> Show "Post Now" (immediate publish), not a scheduled future post — the reviewer needs to see the permission exercised live.

#### Segment D — `threads_content_publish` (Threads publishing)

| Screen | Action | What the reviewer must see |
|--------|--------|---------------------------|
| D1 | Post composer screen | Destination selector showing the connected Threads profile by @handle |
| D2 | Threads selected as publish target | @handle clearly visible and selected |
| D3 | Text (and optional media) entered | Realistic Threads post text typed |
| **D4** | "Publish to Threads" button clicked | Triggers: container creation → processing wait → threads_publish. Show your app's "Processing..." state during the ~30s wait |
| **D5** | In-app success confirmation | "Published to Threads" confirmation in YOUR UI |
| **D6** | Verify on Threads | Open threads.net logged in as the same @handle; show the post appearing on the profile |

> If your app waits 30s before publishing (per Meta's recommendation), show a visible countdown/processing state — a silent 30-second freeze looks like a broken app on camera.

### 7c. App Review Submission Steps

The current Meta portal groups permissions into **Use Cases**. You add use cases first, then fill in details per permission inside each one.

1. From the left sidebar go to **App Review > Permissions and Features** (sometimes shown as **App Review > Requests**).

2. Click **Add use cases**. PersonnaPress requires two tracks:

   **Track 1 — Facebook/Instagram use cases:**

   | Use case | Permissions it covers |
   |----------|-----------------------|
   | Manage and access Page content | `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` |
   | Create and manage Instagram content | `instagram_basic`, `instagram_content_publish` |
   | Manage business assets | `business_management` |

   **Track 2 — Threads use case (configured separately under the Threads product):**

   | Use case | Permissions it covers |
   |----------|-----------------------|
   | Threads (dedicated use case) | `threads_basic`, `threads_content_publish` |

3. Inside each use case, each permission has two steps:
   - **Details**: fill in the "How will you use this permission?" field. Use the descriptions from Section 7d below.
   - **Screencast**: upload the corresponding recording from Section 7b. Every permission must have its own screencast — missing one causes automatic rejection.

4. Fill in **App Details** (left sidebar > App Review > App Details):
   - **App Icon**: 1024×1024 PNG of the PersonnaPress logo
   - **Privacy Policy URL**: `https://personnapress.com/privacy`
   - **Terms of Service URL**: `https://personnapress.com/terms`
   - **App Purpose**: Business and pages management
   - **Category**: Productivity

5. Click **Submit for Review**. Meta will email updates on the review status.

### 7d. Permission Descriptions

Paste these into the "How will you use this permission?" field. **Never copy-paste identical text across multiple permissions** — that is a documented rejection trigger.

---

**`pages_show_list`**

> PersonnaPress is a content publishing tool for marketing agencies. We use `pages_show_list` to retrieve the list of Facebook Pages the authenticated user administers. This lets the user select which Page to publish campaign posts to. We display the Page name in the Connections panel and store only the Page ID, Page name, and Page Access Token — no other Page data is retained.

---

**`pages_read_engagement`**

> We use `pages_read_engagement` to read the name and ID of Facebook Pages connected by the authenticated user. This data is displayed in the PersonnaPress Connections panel so the user can confirm which Page is linked. While this permission grants broader access (including follower data, insights, and profile content), PersonnaPress only reads the Page name and ID — we do not access or store post engagement, comments, reactions, follower data, or audience analytics.

---

**`pages_manage_posts`**

> PersonnaPress uses `pages_manage_posts` to publish marketing campaign content to a connected Facebook Page on behalf of the authenticated Page admin. When a user reviews and approves a campaign in PersonnaPress, we POST the campaign text and optional image link to `/{page_id}/feed` using the Page Access Token. The user controls exactly what is published and when — nothing is posted without explicit approval. This permission is required to publish posts on behalf of a user to a Facebook Page they manage; there is no lower-access alternative that allows Page post creation.

---

**`instagram_basic`**

> We use `instagram_basic` to read the Instagram Business Account ID and username linked to the user's Facebook Page. This identifier is displayed in the PersonnaPress Connections panel so the user can confirm which Instagram account is connected. We do not read posts, stories, comments, followers, DMs, or any analytics data.

---

**`instagram_content_publish`**

> PersonnaPress uses `instagram_content_publish` to publish approved campaign images to Instagram as feed posts. The publish flow: (1) create a media container with the campaign image URL and caption via `/{user_id}/media`, (2) poll `/{container_id}?fields=status_code` until the container status is FINISHED, (3) publish via `/{user_id}/media_publish`. All content is reviewed and approved by the user before it is sent. Captions are capped at 2200 characters per the Instagram API limit. Publishing is not possible with `instagram_basic` alone; this permission is the minimum required to support the feature described above.

---

**`threads_basic`**

> We use `threads_basic` to read the Threads user ID and username associated with the authenticated account. This identifier is displayed in the PersonnaPress Connections panel so the user can confirm which Threads account is connected. While this permission also grants access to a user's posted Threads media and text content, PersonnaPress only reads the account identifier — we do not read, store, or display a user's existing Threads posts, replies, or follower data.

---

**`threads_content_publish`**

> PersonnaPress uses `threads_content_publish` to publish approved campaign content as text posts to Threads. The publish flow: (1) create a TEXT media container via `/{user_id}/threads` with `media_type=TEXT` and the post text, (2) publish via `/{user_id}/threads_publish`. Post text is sourced from the campaign's short-form post field, capped at 280 characters as a product constraint (the Threads API supports up to 500 characters). All content is reviewed and explicitly approved by the user before publishing. `threads_basic` is read-only and does not support publishing; `threads_content_publish` is the minimum permission required to support this feature.

---

**`business_management`**

> `business_management` is required by Facebook Login for Business to verify that the authenticating user has the necessary business-level permissions to manage the Pages and Instagram accounts they are connecting in PersonnaPress. We do not read, modify, or store any business assets, ad accounts, or financial data beyond the Page and Instagram identifiers needed to route publish requests.

---

### 7e. Use Case Description Template

When writing descriptions from scratch or for new permissions, use this template. Fill in the `[brackets]` — and make each permission's text distinct.

```
[App Name] is a social media publishing tool that lets authenticated users
compose and publish posts from a single dashboard to their connected Meta
accounts.

USER FLOW:
1. The user signs in to [App Name] and navigates to [Settings > Connected
   Accounts], where they click [Connect Facebook Page / Connect Instagram /
   Connect Threads] and approve the requested permission in Meta's OAuth dialog.
2. From the [Compose] screen, the user selects their connected
   [Facebook Page name / Instagram account @handle / Threads profile @handle]
   as the destination, enters post text, and optionally attaches [an image / a video].
3. The user clicks the [Publish to Facebook / Publish to Instagram /
   Publish to Threads] button.
4. [App Name] calls the [POST /{page-id}/feed on graph.facebook.com /
   POST /{ig-user-id}/media and POST /{ig-user-id}/media_publish on graph.facebook.com /
   POST /{threads-user-id}/threads and POST /{threads-user-id}/threads_publish on graph.threads.com]
   endpoint(s) to publish the post to the user's own connected account.
5. The user sees an in-app confirmation message ["Post published
   successfully"] with a link to view the live post on [Facebook / Instagram / Threads].

WHY THIS PERMISSION IS REQUIRED:
[PAGES_MANAGE_POSTS ONLY]: This permission is required to publish posts on
behalf of a user to a Facebook Page they manage. There is no lower-access
alternative that allows Page post creation.
[INSTAGRAM_CONTENT_PUBLISH ONLY]: This permission is required to publish
photo and video content to the user's own Instagram Business or Creator
account via the Content Publishing API. Publishing is not possible with
instagram_basic alone.
[THREADS_CONTENT_PUBLISH ONLY]: This permission is required to create and
publish text, image, and video posts to the user's own Threads profile via
the Threads publishing endpoints. threads_basic is read-only and does not
support publishing.

DATA HANDLING:
Post content (text and media URLs) is transmitted directly from our servers
to Meta's API at the moment the user clicks Publish. [We do not store post
content after the publish call completes / We retain published post records
(post ID, timestamp, destination account) for [X days] so users can view
their publishing history]. Only [engineering/support staff with role-based
access] can access this data, and it is deleted [immediately upon account
deletion / within X days of a deletion request]. Our Privacy Policy at [URL]
describes this identically.

ACCESS LEVEL: We are requesting [Standard/Advanced] access, which is the
minimum level that supports the feature described above.
```

**Safe, reviewer-aligned phrasing:**
- "the authenticated user's own connected [Facebook Page / Instagram account / Threads profile]"
- "the user composes the post and clicks Publish"
- "publishes the post to the user's account at the user's explicit action"
- "an in-app confirmation with a link to the live post"
- "Standard/Advanced access is the minimum level that supports this feature"

**Banned phrases (documented rejection triggers):**

| Never write | Why it fails |
|-------------|-------------|
| "to improve user experience" | Generic — gives reviewers nothing to evaluate |
| "core functionality" / "essential for our app" | Zero specificity |
| "We use this data to improve our product" | Doesn't name the data, users, or storage |
| "social features" / "social integration" | Not an evaluable feature name |
| Identical text pasted across multiple permission fields | Signals you don't understand what you requested |

**Dangerous themes to avoid:**

| Avoid implying | Why it's rejected |
|----------------|-------------------|
| Publishing on behalf of OTHER users | Reads as spam/bot infrastructure |
| Automation without a human trigger ("auto-post", "bot posts") | Reviewers require a visible user action per publish |
| AI-generated mass content without user review | Must frame AI as assisting the user who reviews and clicks publish |
| "requesting permissions just in case" | Request only what the demo shows |

### 7f. Pre-Submission Consistency Audit

The description, screencast, and Privacy Policy are cross-checked as a trio. One contradiction = rejection + restart.

| # | Audit item |
|---|------------|
| ☐ | Every feature named in each Use Case description **appears on camera** in the screencast |
| ☐ | Every screen shown in the screencast is **referenced** in at least one description |
| ☐ | Button labels quoted in descriptions **match exactly** what's visible on camera ("Publish to Instagram" != "Post to IG") |
| ☐ | Data-retention claims in descriptions are **worded identically** in the Privacy Policy |
| ☐ | If the Privacy Policy says "no Facebook user data stored server-side" but any description implies processing/storage, **fix before submitting** |
| ☐ | Same test user, same Page, same IG @username, same Threads @handle across all three segments |
| ☐ | Requested access level (Standard vs Advanced) matches the justification given |
| ☐ | Submitted at least one successful API call per permission within 30 days of submission |
| ☐ | All three Use Case descriptions are **distinct texts** — not copy-pasted |

### 7g. Rejection-Recovery Quick Reference

| Rejection code | What it actually means | Fix |
|----------------|------------------------|-----|
| "Unable to verify use case experience in app" | Reviewer couldn't replicate your flow | Show login -> OAuth grant -> publish -> verification as one unbroken take; re-check test credentials work |
| "Fails generic screencast check" | Video looks recycled or staged | Record fresh with real account names, real content, production URL visible |
| "Unable to approve permission request" | Permission never visibly exercised on camera | Add the publish + on-platform verification step (B6/C6/D6) |
| "Insufficient information" | Use case description too vague | Apply the template in Section 7e; name exact screens, buttons, endpoints |
| "Policy concern" | Description implies disallowed use (bulk posting, third-party publishing, automation without user action) | Rewrite using Section 7e safe phrasing |
| Screencast does not show the consent screen | OAuth dialog not visible | Re-record starting from the OAuth button click so the permission dialog is fully visible |
| App not publicly accessible | App behind localhost or VPN | Deploy to a real HTTPS URL before submitting |
| Business not verified | Meta Business Manager verification not complete | Complete Business Verification first |

---

## 8. After Approval

1. Switch the app from Development mode to **Live mode** in App Settings > Basic (toggle at the top of the page).

2. Set `NEXT_PUBLIC_META_PUBLISHING_ENABLED=true` in your production frontend environment.

3. Redeploy the frontend. The Meta Platforms section in the Connections UI will now show an active **Connect** button for all users.

4. Meta long-lived User Access Tokens expire after approximately **60 days**. PersonnaPress obtains a long-lived token during the initial OAuth exchange. If a publish fails with a 401, the user needs to reconnect via the Connections page. A future story can add proactive token refresh or expiry notifications.

5. If a user granted permissions but has not published through PersonnaPress for **90 days**, Meta may require them to re-grant those permissions. Users in this state will need to go through the full OAuth flow again.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| OAuth redirect fails with "URL Blocked" | Redirect URI not added in Facebook Login settings | Add the exact URL from Section 3 |
| "This app is in development mode" error for a real user | App not yet approved or not in Live mode | Add them as Tester (dev) or complete App Review (production) |
| Instagram not appearing after OAuth | Facebook Page has no linked Instagram Business Account | In Instagram app settings, switch to Professional > Business and link the Page |
| Threads not appearing after OAuth | Threads account not linked to the Instagram/Facebook account | Threads discovery runs only if an Instagram Business Account is found; ensure IG is linked first |
| Publish returns 401 | Long-lived token expired (60-day limit) | User must reconnect via Connections page |
| Instagram publish fails with "image URL not accessible" | Image URL is not publicly reachable | Use a CDN-hosted URL; localhost URLs will fail |
| Threads publish shows silent 30s freeze | The backend waits 30 seconds after container creation before calling `threads_publish` (per Meta's recommendation). If the UI has no loading state, it looks frozen. | The backend already handles the 30s wait server-side. The UI must show a visible "Processing..." or spinner state from the moment the user clicks Publish until the success confirmation arrives. |

---

## Official API Reference

- [Threads API — Publishing](https://developers.facebook.com/docs/threads/posts/)
- [Instagram Graph API — Content Publishing](https://developers.facebook.com/docs/instagram-api/guides/content-publishing)
- [Facebook Pages API — Publishing](https://developers.facebook.com/docs/pages/publishing/)
- [Meta App Review Guide](https://developers.facebook.com/docs/app-review/)
