export type ComparisonValue = "yes" | "no" | "partial";

export interface ComparisonRow {
  feature: string;
  personnapress: ComparisonValue;
  competitor: ComparisonValue;
  competitorWin?: boolean;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface Differentiator {
  iconName: string;
  title: string;
  description: string;
}

export interface ComparisonPageData {
  slug: string;
  competitorName: string;
  competitorUrl: string;
  metadata: {
    title: string;
    description: string;
    canonicalPath: string;
  };
  heroAnswer: string;
  verdict: string;
  pricingNote: string;
  comparisonRows: ComparisonRow[];
  competitorStrengths: string[];
  differentiators: Differentiator[];
  faqItems: FaqItem[];
  relatedLinks: Array<{ href: string; label: string }>;
}

export const COMPARISONS: Record<"jasper" | "copy-ai" | "writesonic", ComparisonPageData> = {
  jasper: {
    slug: "jasper-alternatives",
    competitorName: "Jasper",
    competitorUrl: "https://www.jasper.ai",
    metadata: {
      title: "Jasper Alternatives for Founders Who Publish | PersonnaPress",
      description:
        "Looking for a Jasper alternative? Compare PersonnaPress vs Jasper on voice fidelity, autonomous publishing, and price. Honest, fair comparison.",
      canonicalPath: "/jasper-alternatives",
    },
    heroAnswer:
      "The best Jasper alternative depends on your goal. Jasper is built for marketing teams running many agents. If you are a founder who wants one tool to write in your voice, structure content for SEO, and publish to your blog and socials automatically, PersonnaPress covers that whole loop end to end.",
    verdict:
      "Jasper excels at running parallel marketing agent workflows across large teams. PersonnaPress is built for founders and small teams who want one autonomous loop: idea in, SEO-structured article and social posts published to your blog and channels, in your voice, without a handoff step.",
    pricingNote:
      "Jasper entry price: Pro plan from $69 per seat per month (7-day trial, no permanent free tier). As of September 2026, check current pricing at jasper.ai.",
    comparisonRows: [
      { feature: "Brand voice from your own samples", personnapress: "yes", competitor: "yes" },
      { feature: "Consistent long-form voice (2,000+ words)", personnapress: "yes", competitor: "partial" },
      { feature: "Auto-publish to your blog or CMS", personnapress: "yes", competitor: "partial" },
      { feature: "Auto-publish to social (X, LinkedIn, Meta)", personnapress: "yes", competitor: "no" },
      { feature: "SEO structure built into every output", personnapress: "yes", competitor: "partial" },
      {
        feature: "Third-party SEO data integrations (Surfer, Ahrefs)",
        personnapress: "no",
        competitor: "yes",
        competitorWin: true,
      },
      { feature: "Autonomous idea to published loop", personnapress: "yes", competitor: "no" },
      { feature: "Multi-agent marketing platform", personnapress: "no", competitor: "yes", competitorWin: true },
      { feature: "Free to start", personnapress: "yes", competitor: "no" },
    ],
    competitorStrengths: [
      "Mature multi-profile brand voice management across large marketing teams",
      "Broad suite of marketing agents covering ads, emails, and landing pages",
      "Early investment in GEO and AEO content formats",
    ],
    differentiators: [
      {
        iconName: "RefreshCw",
        title: "Idea to published in one loop",
        description:
          "Drop a topic or a brain dump. PersonnaPress writes the SEO-structured article and social posts in your voice, then publishes to your blog and channels. No copy-paste handoff.",
      },
      {
        iconName: "FileText",
        title: "Voice that holds in long-form",
        description:
          "Your voice is extracted from your existing content and held throughout 2,000-word posts, not just short copy. The tone, rhythm, and vocabulary stay consistent from intro to conclusion.",
      },
      {
        iconName: "Share2",
        title: "Blog and social in one workflow",
        description:
          "Publish the article to GitHub, WordPress, Webflow, or the headless API. Publish the social posts to X, LinkedIn, and Meta. One approval, one click, one workflow.",
      },
    ],
    faqItems: [
      {
        question: "What is the main difference between PersonnaPress and Jasper?",
        answer:
          "Jasper is a multi-agent marketing platform designed for teams who need to produce many content types across many channels simultaneously. PersonnaPress is an autonomous publish loop: you submit an idea, it generates an SEO-structured article and social posts in your brand voice, and publishes to your blog and social channels without a manual handoff. If you need marketing agent breadth, Jasper is the better fit. If you want one tool to cover idea to published post, PersonnaPress is built for that.",
      },
      {
        question: "Does Jasper publish directly to my blog?",
        answer:
          "Jasper offers WordPress and HubSpot integrations, but publishing is handled through copy-paste or those integrations rather than a fully autonomous one-click loop. For social media, Jasper does not auto-post natively. PersonnaPress publishes the article and the social posts in one workflow after your single approval.",
      },
      {
        question: "Which tool is better for SEO content?",
        answer:
          "Both tools produce SEO-structured output. Jasper supports a Surfer SEO add-on for keyword scoring and SERP data. PersonnaPress generates SEO-structured HTML with structured headings, meta descriptions, and Schema.org JSON-LD without requiring a third-party add-on, but does not integrate external SEO data tools like Ahrefs or Semrush. If SERP-level keyword data is central to your workflow, Jasper plus Surfer has an advantage there.",
      },
      {
        question: "How much does Jasper cost compared to PersonnaPress?",
        answer:
          "Jasper's Pro plan starts at $69 per seat per month with a 7-day trial and no permanent free tier, as of September 2026 (check current pricing at jasper.ai). PersonnaPress Starter is $29 per month with a 14-day free trial and no credit card required.",
      },
      {
        question: "Can PersonnaPress replace Jasper for a solo founder?",
        answer:
          "If your primary goal is keeping a consistent publishing cadence on your blog and social channels without a large team, yes. PersonnaPress is built around the solo-founder or small-team use case: one voice profile, one autonomous loop from idea to published. Jasper's strength is breadth of agent types across a team, which is less relevant if you are working alone or with one or two people.",
      },
    ],
    relatedLinks: [
      { href: "/copy-ai-alternatives", label: "Copy.ai alternatives" },
      { href: "/writesonic-alternatives", label: "Writesonic alternatives" },
      { href: "/best-ai-blog-writers", label: "Best AI blog writers" },
    ],
  },

  "copy-ai": {
    slug: "copy-ai-alternatives",
    competitorName: "Copy.ai",
    competitorUrl: "https://www.copy.ai",
    metadata: {
      title: "Copy.ai Alternatives for Autonomous Blog Publishing | PersonnaPress",
      description:
        "Looking for a Copy.ai alternative? See how PersonnaPress compares on blog publishing, voice fidelity, and price. Honest, fair comparison.",
      canonicalPath: "/copy-ai-alternatives",
    },
    heroAnswer:
      "Copy.ai is now a GTM AI Platform focused on automating go-to-market workflows. If your goal is keeping a blog updated with content that sounds like you and publishing it automatically to your site and social channels, PersonnaPress is built for that specific loop from start to finish.",
    verdict:
      "Copy.ai has repositioned as a GTM AI Platform for revenue teams, with strong short-form copy and workflow automation. PersonnaPress is built for the publish loop: idea in, SEO-structured long-form article and social posts out, published to your blog and channels in your voice automatically.",
    pricingNote:
      "Copy.ai entry price: Chat plan from $29 per month (no free tier or trial listed). As of September 2026, check current pricing at copy.ai.",
    comparisonRows: [
      { feature: "Brand voice from your own samples", personnapress: "yes", competitor: "yes" },
      { feature: "Consistent long-form voice (2,000+ words)", personnapress: "yes", competitor: "partial" },
      { feature: "Auto-publish to your blog or CMS", personnapress: "yes", competitor: "no" },
      { feature: "Auto-publish to social (X, LinkedIn, Meta)", personnapress: "yes", competitor: "no" },
      { feature: "SEO structure built into every output", personnapress: "yes", competitor: "no" },
      { feature: "GTM workflow automation", personnapress: "no", competitor: "yes", competitorWin: true },
      { feature: "Fast short-form copy generation", personnapress: "partial", competitor: "yes", competitorWin: true },
      { feature: "Autonomous idea to published loop", personnapress: "yes", competitor: "no" },
      { feature: "Free to start", personnapress: "yes", competitor: "no" },
    ],
    competitorStrengths: [
      "Fast short-form copy generation for ads, emails, and social posts",
      "GTM workflow automation for sales and revenue teams",
      "Model flexibility: choice of underlying LLM for different tasks",
    ],
    differentiators: [
      {
        iconName: "RefreshCw",
        title: "Idea to published in one loop",
        description:
          "Drop a topic or a brain dump. PersonnaPress writes the SEO-structured article and social posts in your voice, then publishes to your blog and channels. No copy-paste handoff, no Zapier glue required.",
      },
      {
        iconName: "FileText",
        title: "Voice that holds in long-form",
        description:
          "Your voice is extracted from your existing content and held throughout 2,000-word posts. The tone, rhythm, and vocabulary stay consistent, not just in the intro paragraph.",
      },
      {
        iconName: "Search",
        title: "SEO structure in every article",
        description:
          "Every article PersonnaPress generates includes structured headings, a meta description, and Schema.org JSON-LD. No separate SEO tool or layer to wire in.",
      },
    ],
    faqItems: [
      {
        question: "What is the main difference between PersonnaPress and Copy.ai?",
        answer:
          "Copy.ai is now positioned as a GTM AI Platform, focused on automating sales, marketing, and revenue workflows for teams. It handles short-form copy well and connects to CRM and outreach tools. PersonnaPress is built around a single autonomous loop: submit an idea, get an SEO-structured blog article and social posts in your brand voice, published to your blog and social channels without manual steps. If you need GTM workflow automation, Copy.ai is the better fit. If you need a consistent blog publishing loop, PersonnaPress is built for that.",
      },
      {
        question: "Does Copy.ai publish to my blog?",
        answer:
          "Copy.ai does not include a native blog publishing integration. Publishing requires using Zapier or similar automation tools to move content from Copy.ai to your CMS or blog. PersonnaPress publishes directly to GitHub, WordPress, Webflow, and a headless API, and to X, LinkedIn, and Meta, in one workflow after a single approval.",
      },
      {
        question: "Is there an SEO-focused Copy.ai alternative?",
        answer:
          "PersonnaPress generates SEO-structured articles by default: every post includes structured headings, a meta description, and Schema.org JSON-LD. There is no additional SEO tool or integration to configure. Copy.ai does not include native SEO structuring for long-form content.",
      },
      {
        question: "How much does Copy.ai cost compared to PersonnaPress?",
        answer:
          "Copy.ai's Chat plan starts at $29 per month with no listed free tier or trial, as of September 2026 (check current pricing at copy.ai). PersonnaPress Starter is also $29 per month with a 14-day free trial and no credit card required. The difference is what that price covers: PersonnaPress includes blog publishing and social posting; Copy.ai covers short-form copy and GTM workflows.",
      },
      {
        question: "Can PersonnaPress replace Copy.ai for blog content?",
        answer:
          "For maintaining a blog with content in your own voice and an automated path from idea to published post, yes. Copy.ai is not built around blog publishing or a continuous content loop for a single brand voice. PersonnaPress is. If you also use Copy.ai for sales emails, ad copy, or CRM automation, those workflows are outside PersonnaPress's scope.",
      },
    ],
    relatedLinks: [
      { href: "/jasper-alternatives", label: "Jasper alternatives" },
      { href: "/writesonic-alternatives", label: "Writesonic alternatives" },
      { href: "/best-ai-blog-writers", label: "Best AI blog writers" },
    ],
  },

  writesonic: {
    slug: "writesonic-alternatives",
    competitorName: "Writesonic",
    competitorUrl: "https://writesonic.com",
    metadata: {
      title: "Writesonic Alternatives for Blog and Social Publishing | PersonnaPress",
      description:
        "Looking for a Writesonic alternative? Compare PersonnaPress vs Writesonic on voice fidelity, social publishing, and price. Honest, fair comparison.",
      canonicalPath: "/writesonic-alternatives",
    },
    heroAnswer:
      "Writesonic is a strong AI search and GEO growth engine with deep SEO tool integrations. If you want a tool that also auto-distributes your content to social channels and holds your voice across long-form pieces, PersonnaPress adds the social publishing layer and voice consistency that Writesonic leaves to other tools.",
    verdict:
      "Writesonic is a capable SEO and GEO content platform with strong third-party integrations (Surfer, Ahrefs, Semrush, GSC) and one-click WordPress publishing. PersonnaPress adds native social auto-posting to X, LinkedIn, and Meta, and a voice model built for long-form consistency rather than keyword scoring.",
    pricingNote:
      "Writesonic entry price: Starter plan from $79 per month. As of September 2026, check current pricing at writesonic.com.",
    comparisonRows: [
      { feature: "Brand voice from your own samples", personnapress: "yes", competitor: "yes" },
      { feature: "Consistent long-form voice (2,000+ words)", personnapress: "yes", competitor: "partial" },
      { feature: "Auto-publish to WordPress", personnapress: "yes", competitor: "yes" },
      { feature: "Auto-publish to social (X, LinkedIn, Meta)", personnapress: "yes", competitor: "no" },
      { feature: "SEO structure built into every output", personnapress: "yes", competitor: "yes" },
      {
        feature: "Third-party SEO data integrations (Surfer, Ahrefs, Semrush, GSC)",
        personnapress: "no",
        competitor: "yes",
        competitorWin: true,
      },
      { feature: "GEO / AI-search visibility tracking", personnapress: "no", competitor: "yes", competitorWin: true },
      { feature: "Publish to GitHub, Webflow, headless API", personnapress: "yes", competitor: "no" },
      {
        feature: "Autonomous idea to published loop (blog + social)",
        personnapress: "yes",
        competitor: "partial",
      },
      { feature: "Free to start", personnapress: "yes", competitor: "no" },
    ],
    competitorStrengths: [
      "Deep SEO data integrations: Surfer, Ahrefs, Semrush, and Google Search Console in one tool",
      "GEO module for tracking and improving AI-search visibility",
      "Broad all-in-one breadth covering SEO research, writing, and WordPress publishing",
    ],
    differentiators: [
      {
        iconName: "Share2",
        title: "Blog and social in one workflow",
        description:
          "PersonnaPress publishes the article to your blog (GitHub, WordPress, Webflow, or the headless API) and the social posts to X, LinkedIn, and Meta in one approval. Writesonic publishes to WordPress only with no native social auto-posting.",
      },
      {
        iconName: "FileText",
        title: "Voice that holds in long-form",
        description:
          "Your voice is extracted from your existing content and held throughout 2,000-word posts. Writesonic has documented long-form voice drift after the first few paragraphs. PersonnaPress is built around voice consistency as the core constraint.",
      },
      {
        iconName: "RefreshCw",
        title: "Publish beyond WordPress",
        description:
          "GitHub Pages, Webflow, and any headless CMS via the delivery API are all first-class targets in PersonnaPress. If your stack is not WordPress, PersonnaPress covers it without custom integrations.",
      },
    ],
    faqItems: [
      {
        question: "What is the main difference between PersonnaPress and Writesonic?",
        answer:
          "Writesonic is positioned as an AI search and GEO growth engine, with strong third-party SEO data integrations (Surfer, Ahrefs, Semrush, GSC) and one-click WordPress publishing. PersonnaPress does not integrate external SEO data tools, but it adds what Writesonic does not: native social auto-posting to X, LinkedIn, and Meta, publishing to GitHub, Webflow, and a headless API, and a voice model designed to hold consistently across long-form content.",
      },
      {
        question: "Does Writesonic publish to social media automatically?",
        answer:
          "Writesonic publishes to WordPress with one click but does not include native auto-posting to social channels. Distributing content to X, LinkedIn, or Meta requires separate tools or manual effort. PersonnaPress publishes the blog article and the social posts in one workflow after a single approval.",
      },
      {
        question: "Which tool has better SEO integrations?",
        answer:
          "Writesonic has better SEO data integrations if you use Surfer, Ahrefs, Semrush, or Google Search Console. It pulls keyword scoring, SERP data, and GEO visibility into the writing workflow. PersonnaPress generates SEO-structured output by default (structured headings, meta descriptions, Schema.org JSON-LD) but does not connect to those external data tools. If third-party SEO data is central to your workflow, Writesonic has the advantage there.",
      },
      {
        question: "How much does Writesonic cost compared to PersonnaPress?",
        answer:
          "Writesonic's Starter plan is $79 per month with no permanent free tier, as of September 2026 (check current pricing at writesonic.com). PersonnaPress Starter is $29 per month with a 14-day free trial and no credit card required.",
      },
      {
        question: "Can PersonnaPress replace Writesonic if I publish beyond WordPress?",
        answer:
          "If your blog runs on GitHub Pages, Webflow, or a custom stack using a headless API, PersonnaPress covers all of those targets natively. Writesonic's publishing integration is WordPress-only. If you are already on WordPress and rely heavily on Surfer or Ahrefs data in your content workflow, Writesonic may be the better fit for the SEO research layer.",
      },
    ],
    relatedLinks: [
      { href: "/jasper-alternatives", label: "Jasper alternatives" },
      { href: "/copy-ai-alternatives", label: "Copy.ai alternatives" },
      { href: "/best-ai-blog-writers", label: "Best AI blog writers" },
    ],
  },
};
