import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Globe, Cpu, Send } from "lucide-react";
import { FaqAccordion } from "@/app/_components/FaqAccordion";

export const dynamic = "force-static";

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: { absolute: "Brand Voice Generator | PersonnaPress - Extract Your Voice, Keep It Everywhere" },
    description:
      "PersonnaPress extracts your brand voice from existing content and applies it to every blog post and social update, automatically. No manual style guide required.",
    alternates: {
      canonical: `${APP_URL}/brand-voice-generator`,
    },
    openGraph: {
      title: "Brand Voice Generator | PersonnaPress - Extract Your Voice, Keep It Everywhere",
      description:
        "PersonnaPress extracts your brand voice from existing content and applies it to every blog post and social update, automatically. No manual style guide required.",
      type: "website",
      url: `${APP_URL}/brand-voice-generator`,
      images: [
        {
          url: "/images/PersonnaPress-opengraph.png",
          width: 1200,
          height: 630,
          alt: "PersonnaPress brand voice generator: extract your voice, keep it everywhere",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "Brand Voice Generator | PersonnaPress - Extract Your Voice, Keep It Everywhere",
      description:
        "PersonnaPress extracts your brand voice from existing content and applies it to every blog post and social update, automatically. No manual style guide required.",
    },
  };
}

const jsonLdSoftwareApp = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "PersonnaPress",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: APP_URL,
  description:
    "AI brand voice generator that extracts your tone, cadence, and banned phrases from existing content and applies them to every blog post and social update it generates.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: "14-day free trial, no credit card required",
  },
  featureList: [
    "Brand voice extraction from website content",
    "20-dimension Brand Voice Profile",
    "Tone, cadence, and banned jargon detection",
    "AI blog post generation in your voice",
    "Social post generation matching your style",
    "Voice fidelity scoring per campaign",
  ],
};

const BRAND_VOICE_FAQ = [
  {
    question: "What is a brand voice generator?",
    answer:
      "A brand voice generator is a tool that analyzes existing content to identify consistent patterns in tone, sentence structure, word choice, and vocabulary, then applies those patterns to new content. PersonnaPress goes beyond typical brand voice generators by extracting 20 distinct voice dimensions, including tonal descriptors, sentence cadence, signature phrases, and banned jargon, into a structured Brand Voice Profile that is automatically applied to every blog post, X post, and LinkedIn post the platform generates.",
  },
  {
    question: "What is the difference between brand voice and tone of voice?",
    answer:
      "Brand voice is the consistent personality and character that defines how a brand communicates across all content. It does not change. Tone of voice is how that brand personality adapts in specific contexts: more formal in a whitepaper, friendlier in social media captions, empathetic in a support email. PersonnaPress captures both: the Brand Voice Profile stores your permanent character (tonal descriptors, sentence cadence, banned phrases), while the platform adjusts delivery by content type. A blog post receives different calibration than an X post, while remaining within your voice.",
  },
  {
    question: "How does PersonnaPress extract my brand voice automatically?",
    answer:
      "PersonnaPress runs in three steps. First, you provide source content: paste your website URL (PersonnaPress scrapes your blog posts and public pages automatically) or upload writing samples directly (PDF, Word, or plain text). Second, a voice extraction model analyzes the collected text to identify tonal descriptors, sentence cadence, signature phrases, and banned jargon across 20 dimensions. Third, the results populate a Brand Voice Profile you review and edit field by field before confirming. The entire process takes under 10 minutes.",
  },
  {
    question: "Can AI actually write in my brand voice without sounding generic?",
    answer:
      "Yes, when the AI is trained on your specific content first. Generic AI tools produce generic-sounding output because they have no prior knowledge of your voice. PersonnaPress requires brand voice extraction before generating anything, and all generation is calibrated to your Brand Voice Profile throughout. A voice fidelity score is calculated after each campaign to flag any tonal deviations. Readers familiar with your writing consistently recognize PersonnaPress-generated posts as authentic to their voice.",
  },
  {
    question: "How long does brand voice setup take in PersonnaPress?",
    answer:
      "Under 10 minutes. Paste your website URL and PersonnaPress scrapes your content automatically in about 60 to 90 seconds. Alternatively, upload writing samples directly. Voice extraction runs in another 60 to 90 seconds and produces a full Brand Voice Profile. You review and edit every field before confirming. Most users make no changes. Once confirmed, the profile applies immediately to every campaign you generate.",
  },
];

const jsonLdFaq = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: BRAND_VOICE_FAQ.map(({ question, answer }) => ({
    "@type": "Question",
    name: question,
    acceptedAnswer: {
      "@type": "Answer",
      text: answer,
    },
  })),
};

const HOW_IT_WORKS_STEPS = [
  {
    step: "01",
    icon: Globe,
    title: "Point it at your content",
    description:
      "Paste your website URL or upload writing samples. PersonnaPress scrapes your blog posts and public pages automatically. No copy-paste required.",
  },
  {
    step: "02",
    icon: Cpu,
    title: "Voice extracted in 90 seconds",
    description:
      "AI analysis identifies your tone, cadence, banned phrases, and 17 other voice dimensions. You review and edit every field in the Brand Voice Profile before confirming.",
  },
  {
    step: "03",
    icon: Send,
    title: "Every post sounds like you",
    description:
      "All generated blog posts, X posts, and LinkedIn posts are calibrated to your profile. Voice fidelity is scored after every campaign. Re-run extraction anytime.",
  },
];

const COMPARISON_ROWS = [
  { label: "Setup time", manual: "Days to weeks", personnapress: "Under 10 minutes" },
  { label: "Stays current", manual: "Manual updates required", personnapress: "Re-run extraction anytime" },
  { label: "Applies to every post", manual: "Only if your team follows the guide", personnapress: "Applied automatically, every time" },
  { label: "Catches AI-sounding phrases", manual: "Manual editing required", personnapress: "Built-in fluff detection and removal" },
  { label: "Consistent across platforms", manual: "Varies by author and channel", personnapress: "Same voice on blog, X, and LinkedIn" },
  { label: "Generates content", manual: "No. It is a document, not a tool.", personnapress: "Full campaign in under 90 seconds" },
];

export default function BrandVoiceGeneratorPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdSoftwareApp) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdFaq) }}
      />

      <div className="-mt-8 -mx-4">

        {/* Hero */}
        <section className="max-w-6xl mx-auto px-6 pt-12 md:pt-20 pb-16 md:pb-20">
          <div className="max-w-3xl">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">
              Brand Voice Generator
            </p>
            <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink leading-tight tracking-tight text-balance mb-6">
              Extract Your Voice,{" "}
              <span className="relative">
                Keep It Everywhere.
                <span
                  className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
                  aria-hidden="true"
                />
              </span>
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
              PersonnaPress reads your website and writing samples, then distills your tone,
              cadence, and banned phrases into a living Brand Voice Profile applied to every
              blog post and social update it generates.
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                Start Free Trial
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <a
                href="#how-it-works"
                className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
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

        {/* How It Works */}
        <section id="how-it-works" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              How It Works
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Your brand voice, extracted in minutes
            </h2>
          </header>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border">
            {HOW_IT_WORKS_STEPS.map(({ step, icon: Icon, title, description }) => (
              <div
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
              </div>
            ))}
          </div>
        </section>
        <div className="border-t border-border" />

        {/* Comparison Table */}
        <section className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              The Difference
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Brand voice guide vs. PersonnaPress
            </h2>
          </header>
          <div className="border border-border overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Brand voice guide vs. PersonnaPress comparison</caption>
              <thead>
                <tr className="border-b border-border">
                  <th
                    scope="col"
                    className="p-4 text-left font-mono text-xs text-graphite tracking-widest uppercase w-1/3"
                  >
                    What you get
                  </th>
                  <th
                    scope="col"
                    className="p-4 text-left font-display font-bold text-ink w-1/3 border-l border-border"
                  >
                    Manual brand guide
                  </th>
                  <th
                    scope="col"
                    className="p-4 text-left font-display font-bold text-ink w-1/3 border-l border-border bg-highlight"
                  >
                    PersonnaPress
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_ROWS.map((row) => (
                  <tr key={row.label} className="border-b border-border last:border-b-0">
                    <th scope="row" className="p-4 text-left font-mono text-xs text-graphite">
                      {row.label}
                    </th>
                    <td className="p-4 text-sm text-graphite border-l border-border">{row.manual}</td>
                    <td className="p-4 text-sm text-ink font-medium border-l border-border bg-highlight/30">
                      {row.personnapress}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <div className="border-t border-border" />

        {/* FAQ */}
        <section className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              FAQ
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Brand voice questions answered
            </h2>
          </header>
          <FaqAccordion items={BRAND_VOICE_FAQ} />
        </section>
        <div className="border-t border-border" />

        {/* Footer CTA */}
        <section className="max-w-6xl mx-auto px-6 py-20">
          <div className="border border-ink p-12 shadow-brutal">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Get Started
            </p>
            <h2 className="font-display text-4xl font-bold text-ink mb-4 text-balance">
              Set up your brand voice in 10 minutes.
            </h2>
            <p className="text-graphite mb-2 max-w-lg text-pretty">
              Paste your website URL. PersonnaPress does the rest. Every post you generate
              after that sounds like you.
            </p>
            <p className="font-mono text-xs text-graphite mb-8">
              No credit card required. Cancel anytime.
            </p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Start Your Free Trial
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </section>

      </div>
    </>
  );
}
