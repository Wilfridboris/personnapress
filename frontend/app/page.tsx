import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Mic,
  Cpu,
  ImageIcon,
  CheckCircle2,
  Send,
  Globe,
  Clock,
  Users,
  LayoutDashboard,
  Fingerprint,
  Eraser,
  CalendarCheck,
} from "lucide-react";
import { FaqAccordion } from "./_components/FaqAccordion";
import { PublicHeader } from "@/components/marketing/PublicHeader";
import { PublicFooter } from "@/components/marketing/PublicFooter";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com";

export const metadata: Metadata = {
  title: {
    absolute: "PersonnaPress - AI Blog Writer That Sounds Like You",
  },
  description:
    "PersonnaPress is an AI blog writer that learns your voice and turns your notes into SEO-ranked blog posts and social campaigns. Schedule and publish to WordPress, Webflow, X, and LinkedIn — without sounding like AI.",
  metadataBase: new URL(APP_URL),
  alternates: {
    canonical: APP_URL,
  },
  openGraph: {
    title: "PersonnaPress - AI Blog Writer That Sounds Like You",
    description:
      "Turn your notes into ranked blog posts and social campaigns in your own voice. Schedule and publish everywhere.",
    url: APP_URL,
    type: "website",
    images: [
      {
        url: "/images/PersonnaPress-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PersonnaPress - AI Blog Writer That Sounds Like You",
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
    "An AI blog writer and content engine that turns brain dumps into SEO-ranked blog posts and social campaigns in your authentic voice.",
};

const schemaSoftwareApp = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "PersonnaPress",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: APP_URL,
  description:
    "PersonnaPress is an AI blog writer and social media scheduler that learns your writing voice from existing content, then turns raw brain dumps into SEO-structured blog posts, social campaigns, and featured images. Schedule and publish across WordPress, Webflow, X, and LinkedIn. No AI fluff — content sounds like you, not a robot.",
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
  name: "PersonnaPress",
  url: APP_URL,
  logo: `${APP_URL}/images/PersonnaPress-opengraph.png`,
  description:
    "PersonnaPress is an AI content automation platform that learns your brand voice and publishes SEO-structured content across multiple platforms.",
};

const WORKFLOW_STEPS = [
  {
    step: "01",
    icon: Globe,
    title: "Brand Ingestion",
    description:
      "Paste your website URL and upload past writing samples. PersonnaPress extracts your tone, cadence, and banned jargon into a living brand voice profile.",
  },
  {
    step: "02",
    icon: Mic,
    title: "Brain Dump",
    description:
      "Drop a raw thought, a voice note transcript, or a bullet list. No structure required. That is your only job.",
  },
  {
    step: "03",
    icon: Cpu,
    title: "Draft Generation",
    description:
      "The Hermes agent writes a full SEO blog post (HTML) and matching social posts for X and LinkedIn, calibrated to your exact brand voice.",
  },
  {
    step: "04",
    icon: ImageIcon,
    title: "Media Generation",
    description:
      "FLUX.1 generates a custom featured image matched to your post. Hosted on your server, served for $0.",
  },
  {
    step: "05",
    icon: CheckCircle2,
    title: "Human Approval",
    description:
      "Nothing ships without you. Review the full draft, approve or reject. You stay in control, always.",
  },
  {
    step: "06",
    icon: Send,
    title: "Publishing",
    description:
      "One click publishes to WordPress or Webflow, and schedules posts to X and LinkedIn simultaneously.",
  },
];

const PLATFORMS = ["WordPress", "Webflow", "X (Twitter)", "LinkedIn"];

const PERSONAS = [
  {
    role: "Founders & Executives",
    description:
      "Turn domain expertise into consistent content without writing every word yourself. Set your voice once; the engine handles every post.",
  },
  {
    role: "Solo Coaches",
    description:
      "Publish in your distinctive voice across platforms without hiring a content team. Your audience gets you, not a generic AI.",
  },
  {
    role: "Content Agencies",
    description:
      "Manage multiple client voices from one dashboard. Each client gets a separate Brand Voice Profile; campaigns never cross-contaminate.",
  },
];

const PAIN_POINTS = [
  {
    icon: Clock,
    stat: "6 hours per post",
    description: "Writing takes too long even with generic AI tools that still require heavy editing.",
  },
  {
    icon: Users,
    stat: "Sounds like everyone else",
    description: "No brand voice means no differentiation. Generic AI produces generic content.",
  },
  {
    icon: LayoutDashboard,
    stat: "4 platforms, 4 logins",
    description: "Publishing friction kills consistency. Most teams give up before they build momentum.",
  },
];

const KEY_FEATURES = [
  {
    icon: Fingerprint,
    title: "Voice Profile",
    description:
      "PersonnaPress scrapes your website and past writing to extract your tone, cadence, and banned phrases into a living Brand Voice Profile applied to every campaign.",
  },
  {
    icon: Eraser,
    title: "No AI Fluff",
    description:
      "Detects and strips overused AI phrases like “Unlock the power of”, “Game-changing”, and “Seamlessly”, replacing them with cleaner, more human copy.",
  },
  {
    icon: CalendarCheck,
    title: "Schedule and Publish",
    description:
      "Approve a campaign and publish immediately or schedule it for a future date. One action sends your blog post and social content to every connected platform simultaneously.",
  },
];

const BEFORE_ITEMS = [
  "One blog post takes 6 hours.",
  "Social posts are written separately.",
  "Your content sounds inconsistent.",
  "Publishing is manual across 4 tools.",
  "You disappear when you get busy.",
];

const AFTER_ITEMS = [
  "One idea becomes a full content package.",
  "Everything sounds like you.",
  "Blog and social posts in under 90 seconds.",
  "One click publishes to all your platforms.",
  "You stay visible consistently.",
];

const STARTER_FEATURES = [
  "2 clients",
  "10 campaigns / month",
  "10 image generations / month",
  "WordPress and Webflow publishing",
  "X and LinkedIn scheduling",
  "14-day free trial",
];

const GROWTH_FEATURES = [
  "5 clients",
  "30 campaigns / month",
  "30 image generations / month",
  "Everything in Starter",
  "Content calendar",
  "Scheduled publishing",
];

const AGENCY_FEATURES = [
  "20 clients",
  "Unlimited campaigns",
  "Everything in Growth",
  "Multi-brand workspace",
  "Priority support",
];

const FAQ_ITEMS = [
  {
    question: "What is PersonnaPress and how does it work?",
    answer:
      "PersonnaPress is an AI content engine that learns your exact writing voice, then turns raw ideas into SEO-structured blog posts and social campaigns. You paste a website URL or upload past writing samples, PersonnaPress extracts your tone and style into a Brand Voice Profile, and then any time you submit a brain dump it generates a complete campaign in under 90 seconds.",
  },
  {
    question: "How does PersonnaPress learn my writing voice?",
    answer:
      "PersonnaPress scrapes your website for blog posts and public content, then runs it through a voice extraction model (Gemini 2.5 Flash) that identifies your tone, sentence cadence, and words you never use (banned jargon). The resulting Brand Voice Profile is stored on your account and applied to every campaign. You can review and edit every field before finalizing.",
  },
  {
    question: "What publishing platforms does PersonnaPress support?",
    answer:
      "PersonnaPress currently supports WordPress (self-hosted and WordPress.com), Webflow, X (Twitter), and LinkedIn. Meta / Instagram / Threads are architected and will ship in Phase 2. Each platform integration is independent; a failure on one platform does not block publishing to the others.",
  },
  {
    question: "How long does content generation take?",
    answer:
      "A typical campaign (blog post + X post + LinkedIn post + featured image) generates in under 90 seconds. The 95th-percentile upper bound is 120 seconds. You see real-time progress via a typewriter animation while the pipeline runs.",
  },
  {
    question: "Does PersonnaPress publish content automatically?",
    answer:
      "No. Every draft goes through a human approval gate before anything is published. You review the full campaign, edit it in a WYSIWYG editor if needed, then explicitly approve or reject. Only after your approval can you trigger immediate or scheduled publishing.",
  },
  {
    question: "What is a Brain Dump?",
    answer:
      "A Brain Dump is a free-form text input where you write your raw idea, voice note transcript, or bullet list. It can be between 20 and 10,000 characters. No structure is required. PersonnaPress takes that rough input and transforms it into a polished, on-brand campaign.",
  },
  {
    question: "How is PersonnaPress different from ChatGPT or other AI writing tools?",
    answer:
      "Generic AI tools produce generic-sounding content because they have no knowledge of your voice. PersonnaPress is trained on your specific content before generating anything. It also automates the full pipeline from idea to live post, including featured image generation and multi-platform publishing, which no general-purpose AI tool does.",
  },
  {
    question: "Can I edit the AI-generated content before publishing?",
    answer:
      "Yes. The approval gate includes a full WYSIWYG editor for the blog post and plain-text editors with live character counters for X and LinkedIn posts. You can edit as much or as little as you want before approving.",
  },
  {
    question: "What does the free trial include?",
    answer:
      "The 14-day free trial includes full access to all features: brand voice ingestion, campaign generation, image generation, and publishing to all connected platforms. No credit card is required to start. After 14 days you can subscribe to continue or your account enters a read-only state for 30 days.",
  },
  {
    question: "Is PersonnaPress suitable for agencies managing multiple clients?",
    answer:
      "Yes. PersonnaPress has first-class multi-client support. Each client has a separate Brand Voice Profile, campaign history, and platform connections. You switch between clients from the dashboard. Campaigns never cross-contaminate between clients.",
  },
  {
    question: "Can I publish to WordPress.com (not just self-hosted WordPress)?",
    answer:
      "Yes. PersonnaPress supports both self-hosted WordPress (via Application Password) and WordPress.com (via OAuth 2.0). The WordPress.com OAuth flow handles authentication without requiring you to generate an application password.",
  },
  {
    question: "How are featured images generated?",
    answer:
      "Featured images are generated using FLUX.1 [pro] via the Replicate API. The image is based on your blog post title and content summary, sized at 1200x630 pixels (standard OG/social dimensions), and stored in Supabase Storage. You can request up to 3 regenerations per campaign with an optional prompt override.",
  },
  {
    question: "What is the best AI blog writer for small businesses?",
    answer:
      "PersonnaPress is designed for small businesses and entrepreneurs who need consistent, authentic blog content without a dedicated content team. Unlike generic AI writers, PersonnaPress learns your specific voice, tone, and banned phrases before writing anything. The result is blog posts that sound like you wrote them, not a robot. Posts are also SEO-structured with proper headings and meta descriptions, so they are ready to rank when published.",
  },
  {
    question: "Can I use PersonnaPress to schedule social media posts?",
    answer:
      "Yes. Once you approve a campaign in the Approval Gate, you can publish immediately or set a future date and time for automatic publishing. Your LinkedIn post and X post are scheduled alongside the blog post. You manage everything from one place without switching between tools or logging into each platform separately.",
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

      {/* Navigation */}
      <PublicHeader />

      <main>
        {/* Hero */}
        <section className="max-w-6xl mx-auto px-6 pt-24 pb-20">
          <div className="max-w-3xl">
            <h1 className="font-display text-6xl lg:text-7xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
              The AI Blog Writer{" "}
              <span className="relative">
                That Sounds Like You.
                <span
                  className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
                  aria-hidden="true"
                />
              </span>
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
              Drop in a quick voice memo or brain dump. PersonnaPress learns your
              tone, removes the AI fluff, and turns your notes into published,
              ranked articles in seconds.
            </p>
            <div className="flex items-center gap-4">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
              >
                Create My First Post
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <a
                href="#workflow"
                className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
              >
                See how it works
              </a>
            </div>
            <p className="font-mono text-xs text-graphite mt-4">
              14-day free trial. No credit card required.
            </p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Problem Statement */}
        <section id="problem" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              The Problem
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              AI tools write content that sounds like every other AI
            </h2>
          </header>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border">
            {PAIN_POINTS.map(({ icon: Icon, stat, description }) => (
              <article key={stat} className="bg-paper p-8 group hover:bg-highlight transition-colors">
                <Icon className="size-5 text-graphite mb-6 group-hover:text-ink transition-colors" aria-hidden="true" />
                <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">
                  {stat}
                </h3>
                <p className="text-sm text-graphite leading-relaxed text-pretty">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Who It's For */}
        <section id="for-who" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Built For
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Content that sounds like you, at scale
            </h2>
          </header>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border">
            {PERSONAS.map(({ role, description }) => (
              <article
                key={role}
                className="bg-paper p-8 group hover:bg-highlight transition-colors"
              >
                <h3 className="font-display text-xl font-bold text-ink mb-3">
                  {role}
                </h3>
                <p className="text-sm text-graphite leading-relaxed">{description}</p>
              </article>
            ))}
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Key Features */}
        <section id="features" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Key Features
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Built different from the ground up
            </h2>
          </header>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border">
            {KEY_FEATURES.map(({ icon: Icon, title, description }) => (
              <article key={title} className="bg-paper p-8 group hover:bg-highlight transition-colors">
                <Icon className="size-5 text-graphite mb-6 group-hover:text-ink transition-colors" aria-hidden="true" />
                <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">
                  {title}
                </h3>
                <p className="text-sm text-graphite leading-relaxed text-pretty">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Workflow */}
        <section id="workflow" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              The Workflow
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              From brain dump to published post in minutes
            </h2>
          </header>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px border border-border bg-border">
            {WORKFLOW_STEPS.map(({ step, icon: Icon, title, description }) => (
              <article
                key={step}
                className="bg-paper p-8 group hover:bg-highlight transition-colors"
              >
                <div className="flex items-start justify-between mb-6">
                  <span className="font-mono text-xs text-graphite">{step}</span>
                  <Icon
                    className="size-5 text-graphite group-hover:text-ink transition-colors"
                    aria-hidden="true"
                  />
                </div>
                <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">
                  {title}
                </h3>
                <p className="text-sm text-graphite leading-relaxed text-pretty">
                  {description}
                </p>
              </article>
            ))}
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Before and After */}
        <section id="before-after" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              The Difference
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Life before and after PersonnaPress
            </h2>
          </header>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-px border border-border bg-border">
            <div className="bg-paper p-8">
              <h3 className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">
                Before PersonnaPress
              </h3>
              <ul className="space-y-3">
                {BEFORE_ITEMS.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm text-graphite">
                    <span className="text-graphite mt-0.5" aria-hidden="true">&#8212;</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-highlight p-8">
              <h3 className="font-mono text-xs text-ink tracking-widest uppercase mb-6">
                After PersonnaPress
              </h3>
              <ul className="space-y-3">
                {AFTER_ITEMS.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm text-ink">
                    <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Platforms */}
        <section id="platforms" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-10">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Day-1 Integrations
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Publishes where you already are
            </h2>
          </header>
          <div className="flex flex-wrap gap-4">
            {PLATFORMS.map((platform) => (
              <span
                key={platform}
                className="font-mono text-sm border border-ink px-5 py-3 hover:bg-ink hover:text-paper transition-colors cursor-default"
              >
                {platform}
              </span>
            ))}
          </div>
          <p className="text-sm text-graphite mt-4 font-mono">
            Publishing to GitHub Pages?{" "}
            <Link href="/github-publisher" className="text-ink underline underline-offset-2 hover:text-graphite transition-colors">
              See the GitHub blog publisher
            </Link>
          </p>
          <p className="text-sm text-graphite mt-2 font-mono">
            Building a headless or custom site?{" "}
            <Link href="/headless-blog-api" className="text-ink underline underline-offset-2 hover:text-graphite transition-colors">
              See the Headless Blog API
            </Link>
          </p>
          <p className="text-sm text-graphite mt-2 font-mono">
            Meta / Instagram / Threads: architected, shipping in Phase 2.
          </p>
        </section>

        <div className="border-t border-border" />

        {/* Trial CTA */}
        <section id="trial" className="max-w-6xl mx-auto px-6 py-20">
          <div className="border border-ink p-12 shadow-brutal">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Get Started
            </p>
            <h2 className="font-display text-4xl font-bold text-ink mb-4 text-balance">
              14 days free. Your voice, ranked and published.
            </h2>
            <p className="text-graphite mb-2 max-w-lg text-pretty">
              Set up your brand voice profile in under 10 minutes. Your first campaign draft is ready in 90 seconds.
            </p>
            <p className="font-mono text-xs text-graphite mb-8">
              No credit card required. Cancel anytime.
            </p>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 hover:bg-graphite transition-colors"
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
              <p className="text-sm text-graphite mb-6">For individuals getting started with AI content.</p>
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
                className="inline-flex w-full justify-center items-center gap-2 bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors"
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
                className="inline-flex w-full justify-center items-center gap-2 bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors"
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
                className="inline-flex w-full justify-center items-center gap-2 bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors"
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

      {/* Footer */}
      <PublicFooter />
    </div>
  );
}
