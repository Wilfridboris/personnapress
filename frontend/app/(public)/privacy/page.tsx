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
        PersonnaPress (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) is committed to protecting your privacy.
        This policy explains what data we collect, how we use it, and your rights.
      </p>

      <h2>1. What We Collect</h2>
      <p>We collect the following information when you use PersonnaPress:</p>
      <ul>
        <li>Your email address and password (or Google profile data if you sign in with Google OAuth)</li>
        <li>Website URLs and content you provide for brand voice analysis</li>
        <li>Brain Dump text you enter when creating campaigns</li>
        <li>Files you upload (images and documents for content generation)</li>
      </ul>

      <h2>2. How We Use Your Data</h2>
      <p>We use your data solely to provide the PersonnaPress service:</p>
      <ul>
        <li>
          Blog posts and social content are generated using the{" "}
          <strong>Google Gemini API</strong>. Your content is sent to Google&apos;s
          API for processing.
        </li>
        <li>
          Featured images are generated using the{" "}
          <strong>Replicate API (FLUX 1.1 Pro model)</strong>, developed by Black
          Forest Labs. Images you request may be processed by their infrastructure.
        </li>
        <li>Authentication and session management</li>
        <li>Billing and subscription management via Stripe</li>
      </ul>

      <h2>3. Third-Party Services</h2>
      <p>
        PersonnaPress relies on the following third-party services to operate. Each
        has its own privacy policy:
      </p>
      <ul>
        <li>
          <strong>Google Gemini API</strong>: content generation
        </li>
        <li>
          <strong>Replicate / Black Forest Labs (FLUX 1.1 Pro)</strong>: image
          generation
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
      </ul>
      <p>
        We encourage you to review the privacy policies of these services, as they
        govern how your data is handled on their platforms.
      </p>

      <h2>4. Data Retention</h2>
      <p>
        Your data is retained for the lifetime of your account. After your free
        trial expires and you do not upgrade:
      </p>
      <ul>
        <li>After 30 days your account is flagged for deletion</li>
        <li>A 7-day warning email is sent</li>
        <li>
          After 37 days total, your account and all associated data (clients,
          campaigns, platform connections, uploaded files) are permanently deleted
        </li>
      </ul>

      <h2>5. Your Rights</h2>
      <p>
        You can delete your account at any time from the{" "}
        <Link href="/account">Account page</Link>. Deleting your account permanently
        removes all your clients, campaigns, platform connections, and uploaded files.
        This action cannot be undone.
      </p>

      <h2>6. Cookies</h2>
      <p>
        We use a single session cookie (httpOnly, 7-day expiry) for authentication
        only. We do not use tracking cookies, advertising cookies, or any
        third-party analytics cookies.
      </p>

      <h2>7. Contact</h2>
      <p>
        If you have questions about this policy, contact us at{" "}
        <a href="mailto:support@personnapress.com">support@personnapress.com</a>.
      </p>
    </article>
  );
}
