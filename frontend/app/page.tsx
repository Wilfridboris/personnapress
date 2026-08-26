import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { FaqAccordion } from "./_components/FaqAccordion";
import { PublicHeader } from "@/components/marketing/PublicHeader";
import { PublicFooter } from "@/components/marketing/PublicFooter";
import { EmailCaptureWidget } from "@/components/marketing/EmailCaptureWidget";
import { PlatformIcon } from "@/components/ui/PlatformIcon";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com";

export const metadata: Metadata = {
  title: {
    absolute: "PersonnaPress | Official Site - AI Content Platform",
  },
  description:
    "PersonnaPress learns your brand voice and turns ideas into SEO-ranked blog posts and social campaigns. Publishes to WordPress, Webflow, LinkedIn, and X.",
  metadataBase: new URL(APP_URL),
  alternates: {
    canonical: APP_URL,
  },
  openGraph: {
    title: "PersonnaPress | Official Site - The AI Content Platform That Publishes in Your Brand Voice",
    description:
      "Turn rough ideas into blog posts and social campaigns in your brand voice. You approve everything before it goes live. Publishes to WordPress, Webflow, LinkedIn, and X.",
    url: APP_URL,
    type: "website",
    images: [
      {
        url: "/images/PersonnaPress-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PersonnaPress - The AI Content Platform That Publishes in Your Brand Voice",
      },
    ],
  },
};

const schemaWebsite = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "PersonnaPress",
  url: APP_URL,
  description:
    "An AI content platform that learns your brand voice and generates SEO-ranked blog posts, social campaigns, and featured images in your authentic style. Publishes to WordPress, Webflow, LinkedIn, and X.",
};

const schemaSoftwareApp = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "PersonnaPress",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: APP_URL,
  description:
    "PersonnaPress is an AI-powered content platform that extracts your brand voice from existing content, then turns raw ideas into SEO-structured blog posts, social campaigns, and featured images in your authentic voice. Nothing publishes until you review and approve it.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: "14-day free trial, no credit card required",
  },
  featureList: [
    "Brand voice extraction from existing content",
    "AI blog post generation (SEO-structured HTML)",
    "X (Twitter) and LinkedIn social post generation",
    "AI featured image generation via FLUX.1",
    "No AI fluff detection and removal",
    "Scheduled social media publishing",
    "Human approval gate before any publish",
    "WordPress and Webflow publishing",
    "Multi-client agency management",
  ],
};

const schemaOrganization = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": `${APP_URL}/#organization`,
  name: "PersonnaPress",
  legalName: "PersonnaPress",
  url: APP_URL,
  logo: {
    "@type": "ImageObject",
    url: `${APP_URL}/images/PersonnaPress-opengraph.png`,
    width: 1200,
    height: 630,
  },
  description:
    "PersonnaPress is an AI-powered software application, not a PR agency or publishing house, that extracts your brand voice and generates SEO-ranked blog posts, social campaigns, and featured images in your authentic style. Founded by Boris Kwayep.",
  founder: {
    "@type": "Person",
    name: "Boris Kwayep",
    url: `${APP_URL}/about`,
  },
  sameAs: [
    "https://www.facebook.com/personnapress/",
  ],
  knowsAbout: [
    "AI content generation",
    "Brand voice extraction",
    "SEO blog writing",
    "Social media content automation",
    "WordPress publishing",
    "Webflow publishing",
    "LinkedIn content marketing",
    "GitHub Pages publishing",
    "Headless blog API",
  ],
};

const PLATFORMS = [
  { label: "WordPress",   platform: "wordpress" },
  { label: "Webflow",     platform: "webflow" },
  { label: "X (Twitter)", platform: "x" },
  { label: "LinkedIn",    platform: "linkedin" },
];

const ROI_ITEMS = [
  "One idea becomes a full content package: blog post, social posts, and a featured image.",
  "Everything sounds like you wrote it.",
  "Blog and social drafts are ready in under ninety seconds.",
  "Your first post can be live within fifteen minutes of signing up.",
  "One click publishes to all your connected platforms at once.",
  "You stay visible consistently, even in your busiest weeks.",
];

const STARTER_FEATURES = [
  "2 clients",
  "10 campaigns per month",
  "1 weekly roadmap per month",
  "10 image generations per month",
  "All publishing platforms (WordPress, GitHub)",
  "X and LinkedIn publishing",
  "Brand voice profiles",
  "Content calendar",
  "Scheduled publishing",
  "Headless blog API",
  "14-day free trial",
];

const GROWTH_FEATURES = [
  "5 clients",
  "30 campaigns per month",
  "4 weekly roadmaps per month",
  "30 image generations per month",
  "Everything in Starter",
];

const AGENCY_FEATURES = [
  "20 clients",
  "Unlimited campaigns",
  "Unlimited weekly roadmaps",
  "100 image generations per month",
  "Everything in Growth",
  "Priority support",
];

const FAQ_ITEMS = [
  {
    question: "Does PersonnaPress publish content automatically?",
    answer:
      "No. Every draft goes through a human approval gate before anything is published. You review the full campaign, edit it if needed, and explicitly approve it. Only after your approval can you trigger immediate or scheduled publishing.",
  },
  {
    question: "How does it learn my writing voice?",
    answer:
      "PersonnaPress scrapes your website and past writing samples to extract your tone, sentence cadence, and the phrases you never use. The result is a Brand Voice Profile stored on your account and applied to every campaign you generate. You can review and edit every field before finalizing it.",
  },
  {
    question: "What does the free trial include?",
    answer:
      "The 14-day free trial includes full access to all features: brand voice ingestion, campaign generation, image generation, and publishing to all connected platforms. No credit card is required to start. After 14 days you can subscribe to continue, or your account enters a read-only state for 30 days.",
  },
  {
    question: "Can I edit the AI-generated content before publishing?",
    answer:
      "Yes. The approval gate includes a full WYSIWYG editor for the blog post and plain-text editors with live character counters for your X and LinkedIn posts. You can edit as much or as little as you want before approving.",
  },
];

const schemaFaq = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ_ITEMS.map(({ question, answer }) => ({
    "@type": "Question",
    name: question,
    acceptedAnswer: {
      "@type": "Answer",
      text: answer,
    },
  })),
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-paper">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaWebsite) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaSoftwareApp) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaOrganization) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaFaq) }}
      />

      <PublicHeader />

      <main>
        {/* Hero */}
        <section className="max-w-6xl mx-auto px-6 pt-12 md:pt-24 pb-16 md:pb-20">
          <div className="max-w-3xl">
            <h1 className="font-display text-4xl sm:text-5xl lg:text-7xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
              The AI Content Platform{" "}
              <span className="relative">
                That Publishes in Your Brand Voice.
                <span
                  className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
                  aria-hidden="true"
                />
              </span>
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
              Turn a rough idea into a blog post and social campaign that sound like you wrote
              them, not a robot. You approve every word before anything goes live.
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                Create My First Post
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </div>
            <p className="font-mono text-xs text-graphite mt-4">
              14-day free trial. No credit card required.
            </p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Pillar 1 - FIT: text left / image right */}
        <section id="built-for" className="max-w-6xl mx-auto px-6 py-20">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-24 items-center">
            <div>
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                Built For
              </p>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-ink text-balance mb-6 leading-tight">
                Built for the person who has the expertise, not the afternoon.
              </h2>
              <p className="text-graphite leading-relaxed text-pretty">
                Founders turning domain know-how into consistent weekly posts, without writing
                every word themselves. Coaches who publish in their own distinctive voice and plan
                a full week in one sitting. Agencies managing each client's voice as its own, so
                no one can tell the posts came from the same desk.
              </p>
            </div>
            <div className="border border-border overflow-hidden">
              <Image
                src="/images/landing/dashboard-overview.png"
                alt="PersonnaPress dashboard showing an active content campaign with brand voice settings and platform connections"
                width={640}
                height={400}
                sizes="(max-width: 768px) 100vw, 50vw"
                priority
                className="w-full h-auto"
              />
            </div>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Pillar 2 - VOICE: image left / text right */}
        <section id="brand-voice" className="max-w-6xl mx-auto px-6 py-20">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-24 items-center">
            <div className="md:order-2">
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                Your Voice
              </p>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-ink text-balance mb-6 leading-tight">
                It learns your voice first. Then you approve everything.
              </h2>
              <p className="text-graphite leading-relaxed text-pretty">
                PersonnaPress reads your existing writing and builds a Brand Voice Profile: your
                tone, your sentence cadence, the phrases you never use. Every draft is written
                inside that profile and scored against it before you see it. Nothing publishes
                until you review it, edit it if you want, and say yes. That's the only path to
                live.
              </p>
            </div>
            <div className="border border-border overflow-hidden md:order-1">
              <Image
                src="/images/landing/voice-profile.png"
                alt="PersonnaPress Brand Voice Profile showing extracted tone settings, sentence cadence analysis, and a list of banned phrases"
                width={640}
                height={400}
                sizes="(max-width: 768px) 100vw, 50vw"
                loading="lazy"
                className="w-full h-auto"
              />
            </div>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Pillar 3 - ROI: text left / image right */}
        <section id="results" className="max-w-6xl mx-auto px-6 py-20">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-24 items-center">
            <div>
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                The Result
              </p>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-ink text-balance mb-6 leading-tight">
                Six hours of writing becomes ninety seconds of review.
              </h2>
              <ul className="space-y-3">
                {ROI_ITEMS.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm text-graphite">
                    <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="border border-border overflow-hidden">
              <Image
                src="/images/landing/plan-my-week.png"
                alt="PersonnaPress Plan My Week interface showing a full week of content scheduled across blog and social platforms"
                width={640}
                height={400}
                sizes="(max-width: 768px) 100vw, 50vw"
                loading="lazy"
                className="w-full h-auto"
              />
            </div>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Pillar 4 - FIT-SYSTEM: image left / text right */}
        <section id="integrations" className="max-w-6xl mx-auto px-6 py-20">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-24 items-center">
            <div className="md:order-2">
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                Integrations
              </p>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-ink text-balance mb-6 leading-tight">
                Publishes where you already are.
              </h2>
              <p className="text-graphite leading-relaxed text-pretty mb-8">
                WordPress, Webflow, LinkedIn, and X, from one place. No new dashboard to check.
                No fifth login to remember. PersonnaPress fits the content workflow you already
                run, and does not ask you to change it.
              </p>
              <div className="flex flex-wrap gap-3">
                {PLATFORMS.map(({ label, platform }) => (
                  <span
                    key={label}
                    className="inline-flex items-center gap-2 font-mono text-sm border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors cursor-default"
                  >
                    <PlatformIcon platform={platform} className="size-4" color="mono" aria-hidden="true" />
                    {label}
                  </span>
                ))}
              </div>
            </div>
            <div className="border border-border overflow-hidden md:order-1">
              <Image
                src="/images/landing/connections.png"
                alt="PersonnaPress Connections screen showing active platform connections to WordPress, Webflow, LinkedIn, and X"
                width={640}
                height={400}
                sizes="(max-width: 768px) 100vw, 50vw"
                loading="lazy"
                className="w-full h-auto"
              />
            </div>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Trigger band */}
        <section id="trial" className="max-w-6xl mx-auto px-6 py-20">
          <div className="border border-ink p-12 shadow-brutal">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Get Started
            </p>
            <h2 className="font-display text-3xl sm:text-4xl font-bold text-ink mb-4 text-balance">
              14 days free. Your first draft ready in ninety seconds.
            </h2>
            <p className="text-graphite mb-8 max-w-lg text-pretty">
              No credit card required. Cancel anytime. You approve every post before it goes
              anywhere.
            </p>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Start Your Free Trial
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Pricing */}
        <section id="pricing" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Pricing
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Simple, transparent pricing
            </h2>
          </header>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border">
            {/* Starter */}
            <article className="bg-paper p-8">
              <h3 className="font-display text-2xl font-bold text-ink mb-1">Starter</h3>
              <p className="font-display text-4xl font-bold text-ink mb-1">
                $29<span className="font-mono text-sm text-graphite">/mo</span>
              </p>
              <p className="text-sm text-graphite mb-6">For individuals getting started with AI content automation.</p>
              <ul className="space-y-2 mb-8">
                {STARTER_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-graphite">
                    <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/dashboard"
                className="inline-flex w-full justify-center items-center gap-2 bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                Start Free
                <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </article>

            {/* Growth */}
            <article className="bg-paper p-8">
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-2">
                Most popular
              </p>
              <h3 className="font-display text-2xl font-bold text-ink mb-1">Growth</h3>
              <p className="font-display text-4xl font-bold text-ink mb-1">
                $49<span className="font-mono text-sm text-graphite">/mo</span>
              </p>
              <p className="text-sm text-graphite mb-6">For businesses that publish weekly.</p>
              <ul className="space-y-2 mb-8">
                {GROWTH_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-graphite">
                    <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/dashboard"
                className="inline-flex w-full justify-center items-center gap-2 bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                Start Free Trial
                <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </article>

            {/* Agency */}
            <article className="bg-paper p-8">
              <h3 className="font-display text-2xl font-bold text-ink mb-1">Agency</h3>
              <p className="font-display text-4xl font-bold text-ink mb-1">
                $149<span className="font-mono text-sm text-graphite">/mo</span>
              </p>
              <p className="text-sm text-graphite mb-6">For agencies managing multiple client voices.</p>
              <ul className="space-y-2 mb-8">
                {AGENCY_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-graphite">
                    <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/dashboard"
                className="inline-flex w-full justify-center items-center gap-2 bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                Book a Demo
                <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </article>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* FAQ */}
        <section id="faq" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              FAQ
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Frequently asked questions
            </h2>
          </header>
          <FaqAccordion items={FAQ_ITEMS} />
        </section>
      </main>

      <EmailCaptureWidget source="homepage" />

      <PublicFooter />
    </div>
  );
}
