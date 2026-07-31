import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy | PersonnaPress",
  description: "PersonnaPress Privacy Policy",
  robots: { index: true, follow: true },
};

export default function PrivacyPage() {
  return (
    <article className="prose max-w-3xl mx-auto px-6 py-12">
      <p className="not-prose mb-6">
        <Link href="/" className="text-sm text-[#555555] hover:text-[#111111] underline underline-offset-2">
          Back to PersonnaPress
        </Link>
      </p>

      <h1>Privacy Policy</h1>
      <p className="lead">Effective date: July 2026</p>

      <p>
        PersonnaPress (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) is
        committed to protecting your privacy. This policy explains what data we
        collect, how we use it, and your rights.
      </p>

      <h2>1. What We Collect</h2>
      <p>We collect the following information when you use PersonnaPress:</p>
      <ul>
        <li>
          Your email address and hashed password, or your Google profile
          information (name, email, Google account ID) if you sign in with
          Google OAuth
        </li>
        <li>
          Website URLs and content you provide for brand voice analysis
        </li>
        <li>Brain Dump text you enter when creating campaigns</li>
        <li>Files you upload (images and documents for content generation)</li>
        <li>Billing information processed by Stripe (we do not store card numbers)</li>
      </ul>

      <h3>Social Platform Connections</h3>
      <p>
        When you connect a social platform or publishing destination,
        PersonnaPress stores the OAuth credentials required to publish on your
        behalf. Specifically:
      </p>
      <ul>
        <li>
          <strong>Facebook Pages and Instagram</strong>: encrypted Page Access
          Tokens, long-lived user tokens, Facebook Page IDs, Instagram Business
          Account user IDs, and account display names
        </li>
        <li>
          <strong>Threads</strong>: encrypted long-lived user access tokens and
          Threads user IDs
        </li>
        <li>
          <strong>X (Twitter)</strong>: encrypted OAuth 2.0 access and refresh
          tokens
        </li>
        <li>
          <strong>LinkedIn</strong>: encrypted OAuth 2.0 access tokens and
          LinkedIn member URNs
        </li>
        <li>
          <strong>WordPress.com</strong>: encrypted OAuth access tokens and site
          identifiers
        </li>
        <li>
          <strong>WordPress (self-hosted)</strong>: credentials you provide
          (stored encrypted)
        </li>
        <li>
          <strong>GitHub Pages</strong>: GitHub App installation IDs and
          repository identifiers
        </li>
        <li>
          <strong>Webflow</strong>: encrypted API tokens and site identifiers
        </li>
      </ul>
      <p>
        All OAuth tokens are encrypted at rest. We do not collect or store your
        social posts, followers, messages, or any other content from connected
        platforms beyond what is necessary to authenticate and publish.
      </p>

      <h2>2. How We Use Your Data</h2>
      <p>We use your data solely to provide the PersonnaPress service:</p>
      <ul>
        <li>
          Blog posts and social content are generated using an AI language
          model. Depending on your account configuration, content may be
          processed by the <strong>Google Gemini API</strong> or the{" "}
          <strong>Anthropic Claude API</strong>. Your content is sent to the
          active AI provider for processing.
        </li>
        <li>
          Featured images are generated using the{" "}
          <strong>Replicate API (FLUX 1.1 Pro model)</strong>, developed by
          Black Forest Labs. Images you request may be processed by their
          infrastructure.
        </li>
        <li>Authentication and session management</li>
        <li>Billing and subscription management via Stripe</li>
        <li>
          Publishing content to platforms you have connected (Facebook Pages,
          Instagram, Threads, X, LinkedIn, WordPress, GitHub Pages, Webflow)
          using the OAuth credentials you authorized
        </li>
      </ul>

      <h2>3. Third-Party Services</h2>
      <p>
        PersonnaPress relies on the following third-party services to operate.
        Each has its own privacy policy:
      </p>
      <ul>
        <li>
          <strong>Google Gemini API</strong>: content generation (optional AI
          provider)
        </li>
        <li>
          <strong>Anthropic (Claude API)</strong>: content generation (default
          AI provider)
        </li>
        <li>
          <strong>Replicate / Black Forest Labs (FLUX 1.1 Pro)</strong>: image
          generation
        </li>
        <li>
          <strong>Meta (Facebook, Instagram, Threads)</strong>: publishing
          integration via the Meta Graph API and Threads API
        </li>
        <li>
          <strong>X Corp (Twitter)</strong>: publishing integration via the X
          API v2
        </li>
        <li>
          <strong>LinkedIn</strong>: publishing integration via the LinkedIn API
        </li>
        <li>
          <strong>WordPress.com / Automattic</strong>: publishing integration
        </li>
        <li>
          <strong>GitHub</strong>: publishing integration via the GitHub App API
        </li>
        <li>
          <strong>Webflow</strong>: publishing integration via the Webflow API
        </li>
        <li>
          <strong>Stripe</strong>: billing and payment processing
        </li>
        <li>
          <strong>Supabase</strong>: data storage and file hosting
        </li>
        <li>
          <strong>Vercel</strong>: frontend hosting and edge delivery
        </li>
        <li>
          <strong>Resend</strong>: transactional email (account verification,
          notifications)
        </li>
        <li>
          <strong>Sentry</strong>: error monitoring (anonymized stack traces;
          no personal content is sent)
        </li>
      </ul>
      <p>
        We encourage you to review the privacy policies of these services, as
        they govern how your data is handled on their platforms.
      </p>

      <h2>4. Data Retention</h2>
      <p>
        Your data is retained for the lifetime of your account. OAuth tokens
        for connected platforms are deleted immediately when you disconnect a
        platform or when your account is deleted.
      </p>
      <p>After your free trial expires and you do not upgrade:</p>
      <ul>
        <li>After 30 days your account is flagged for deletion</li>
        <li>A 7-day warning email is sent</li>
        <li>
          After 37 days total, your account and all associated data (clients,
          campaigns, platform connections, uploaded files, and OAuth tokens) are
          permanently deleted
        </li>
      </ul>

      <h2>5. Meta Platform Data and Data Deletion</h2>
      <p>
        PersonnaPress is a registered Meta app that uses the Meta Graph API to
        publish to Facebook Pages, Instagram Business Accounts, and Threads.
        In accordance with Meta&apos;s Platform Terms:
      </p>
      <ul>
        <li>
          We only request the permissions necessary to publish content on your
          behalf:{" "}
          <code>
            instagram_content_publish, pages_manage_posts,
            threads_content_publish
          </code>{" "}
          and the read permissions required to discover your connected accounts.
        </li>
        <li>
          We do not access or store your personal Facebook profile, friend
          lists, private messages, or any data beyond platform tokens and
          account identifiers.
        </li>
        <li>
          Meta may notify us when you remove PersonnaPress from your Facebook
          app settings. We process this notification and log it; to fully
          remove all associated data, follow the steps on our{" "}
          <Link href="/data-deletion">Data Deletion page</Link>.
        </li>
      </ul>
      <p>
        To delete all data PersonnaPress holds from your Meta platform
        connections, visit our{" "}
        <Link href="/data-deletion">Data Deletion page</Link> or delete your
        PersonnaPress account from{" "}
        <Link href="/settings">Account Settings</Link>.
      </p>

      <h2>6. Your Rights</h2>
      <p>
        Depending on your location, you may have the following rights regarding
        your personal data:
      </p>
      <ul>
        <li>
          <strong>Access</strong>: request a copy of the personal data we hold
          about you
        </li>
        <li>
          <strong>Deletion</strong>: request that we delete your personal data.
          You can do this immediately by deleting your account from the{" "}
          <Link href="/settings">Settings page</Link>, or by contacting us.
        </li>
        <li>
          <strong>Correction</strong>: request correction of inaccurate data
        </li>
        <li>
          <strong>Portability</strong>: request a machine-readable export of
          your data
        </li>
        <li>
          <strong>Objection</strong>: object to certain processing of your data
        </li>
      </ul>
      <p>
        To exercise any of these rights, email us at{" "}
        <a href="mailto:support@personnapress.com">support@personnapress.com</a>{" "}
        with the subject line &ldquo;Privacy Request&rdquo;. We will respond
        within 30 days.
      </p>
      <p>
        You can also delete your account at any time directly from the{" "}
        <Link href="/settings">Settings page</Link>. Deleting your account
        permanently removes all your data. This action cannot be undone.
      </p>

      <h2>7. Cookies</h2>
      <p>
        We use the following cookies only:
      </p>
      <ul>
        <li>
          <strong>Session cookie</strong> (httpOnly, 7-day expiry): used for
          authentication only
        </li>
        <li>
          <strong>OAuth state cookies</strong> (httpOnly, 10-minute expiry):
          short-lived cookies set during platform OAuth flows to prevent
          cross-site request forgery. Deleted immediately after the OAuth flow
          completes.
        </li>
      </ul>
      <p>
        We do not use tracking cookies, advertising cookies, or any third-party
        analytics cookies.
      </p>

      <h2>8. Contact</h2>
      <p>
        If you have questions about this policy, contact us at{" "}
        <a href="mailto:support@personnapress.com">support@personnapress.com</a>.
      </p>
    </article>
  );
}
