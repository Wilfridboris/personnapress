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
} from "lucide-react";
export const metadata: Metadata = {
  title: "PersonaPress - Publish in Your Voice, Not AI's",
  description:
    "PersonaPress turns your raw brain dumps into SEO-ranked blog posts and social campaigns that sound exactly like you. Built for founders, coaches, and agencies.",
  alternates: {
    canonical: "https://personapress.io",
  },
  openGraph: {
    title: "PersonaPress - Publish in Your Voice, Not AI's",
    description:
      "Turn raw ideas into published, ranked content. Your voice, your style, every time.",
    url: "https://personapress.io",
    type: "website",
  },
};

const jsonLd: Record<string, unknown> = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "PersonaPress",
  url: "https://personapress.io",
  description:
    "An autonomous content engine that turns brain dumps into SEO-ranked blog posts and social campaigns in your authentic voice.",
};

const WORKFLOW_STEPS = [
  {
    step: "01",
    icon: Globe,
    title: "Brand Ingestion",
    description:
      "Paste your website URL and upload past writing samples. PersonaPress extracts your tone, cadence, and banned jargon into a living brand voice profile.",
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

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-paper">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Navigation */}
      <header className="border-b border-border sticky top-0 bg-paper z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="font-display text-xl font-bold text-ink tracking-tight">
            PersonaPress
          </span>
          <nav className="flex items-center gap-8">
            <a
              href="#workflow"
              className="text-sm text-graphite hover:text-ink transition-colors"
            >
              How it works
            </a>
            <a
              href="#platforms"
              className="text-sm text-graphite hover:text-ink transition-colors"
            >
              Platforms
            </a>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-2 hover:bg-graphite transition-colors"
            >
              Open App
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="max-w-6xl mx-auto px-6 pt-24 pb-20">
          <div className="max-w-3xl">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-8 border border-border inline-block px-3 py-1">
              Autonomous Content Engine
            </p>
            <h1 className="font-display text-6xl lg:text-7xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
              Your Ideas.
              <br />
              Published and Ranked.
              <br />
              <span className="relative">
                In Your Voice.
                <span
                  className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
                  aria-hidden="true"
                />
              </span>
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
              Stop spending 6 hours writing blog posts that sound like every other
              AI-generated article. PersonaPress learns your voice from your past
              content, then turns your raw brain dumps into ranked posts and social
              campaigns.
            </p>
            <div className="flex items-center gap-4">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
              >
                Start Publishing
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <a
                href="#workflow"
                className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
              >
                See how it works
              </a>
            </div>
          </div>
        </section>

        {/* Divider */}
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

        {/* Divider */}
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
          <p className="text-sm text-graphite mt-6 font-mono">
            Meta / Instagram / Threads: architected, shipping in Phase 2.
          </p>
        </section>

        {/* Divider */}
        <div className="border-t border-border" />

        {/* CTA */}
        <section className="max-w-6xl mx-auto px-6 py-20">
          <div className="border border-ink p-12 shadow-brutal">
            <h2 className="font-display text-4xl font-bold text-ink mb-4 text-balance">
              Ready to stop writing and start publishing?
            </h2>
            <p className="text-graphite mb-8 max-w-lg text-pretty">
              Set up your brand voice profile in under 10 minutes. Your first
              campaign draft is waiting.
            </p>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 hover:bg-graphite transition-colors"
            >
              Open PersonaPress
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-8 flex items-center justify-between">
          <span className="font-display font-bold text-ink">PersonaPress</span>
          <p className="font-mono text-xs text-graphite">
            Your Ideas, Published and Ranked.
          </p>
        </div>
      </footer>
    </div>
  );
}
