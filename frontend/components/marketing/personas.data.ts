export interface FaqItem {
  question: string;
  answer: string;
}

export interface Pain {
  title: string;
  description: string;
}

export interface Solution {
  iconName: string;
  title: string;
  description: string;
}

export interface PersonaPageData {
  slug: string;
  persona: string;
  primaryKeyword: string;
  metadata: {
    title: string;
    description: string;
    canonicalPath: string;
  };
  h1: string;
  breadcrumbLabel: string;
  heroAnswer: string;
  painsHeading: string;
  solutionsHeading: string;
  pains: Pain[];
  solutions: Solution[];
  faqItems: FaqItem[];
  relatedLinks: Array<{ href: string; label: string }>;
}

export const PERSONAS: Record<"saas" | "coaches" | "agencies", PersonaPageData> = {
  saas: {
    slug: "ai-blog-writer-for-saas-founders",
    persona: "SaaS Founders",
    primaryKeyword: "content marketing for saas",
    metadata: {
      title: "AI Blog Writer for SaaS Founders That Ranks in Your Voice",
      description:
        "PersonnaPress is the AI blog writer built for SaaS founders: it learns your brand voice from your existing content, writes SEO-structured articles, and publishes to your blog and social channels automatically. No ghostwriter. No copy-paste.",
      canonicalPath: "/ai-blog-writer-for-saas-founders",
    },
    h1: "AI Blog Writer for SaaS Founders That Ranks in Your Voice",
    breadcrumbLabel: "AI Blog Writer for SaaS Founders",
    painsHeading: "Why your blog stays empty",
    solutionsHeading: "The full publish loop, in your voice",
    heroAnswer:
      "The best AI blog writer for SaaS founders is one that learns your product voice from your own writing, generates SEO-structured long-form articles without generic filler, and publishes to your blog and social channels automatically. PersonnaPress covers that full loop so you can ship product content without hiring a content team.",
    pains: [
      {
        title: "You ship features but your blog stays empty",
        description:
          "Every week you have product insights worth publishing. But writing, editing, and scheduling takes hours you don't have, so the blog collects dust while competitors rank for your keywords.",
      },
      {
        title: "Generic AI content sounds nothing like you",
        description:
          "Off-the-shelf AI writers produce passable text that loses your voice after the first paragraph. Readers can tell. So can search engines that reward demonstrated expertise and consistent authorship signals.",
      },
      {
        title: "Blog to social is a separate manual job",
        description:
          "Even when an article is finished, you still need to cut it into LinkedIn posts, X threads, and social copy. That second job never gets done, and your content reach stays narrow.",
      },
    ],
    solutions: [
      {
        iconName: "FileText",
        title: "Brand voice extracted from your writing",
        description:
          "PersonnaPress reads your existing posts, landing pages, and emails to extract your tone, vocabulary, and rhythm. Every article it generates holds that voice throughout, from intro to conclusion.",
      },
      {
        iconName: "RefreshCw",
        title: "Idea to published in one loop",
        description:
          "Drop a topic or a brain dump. PersonnaPress writes the SEO-structured article and social posts, then publishes to your blog and channels. One approval, no copy-paste handoff.",
      },
      {
        iconName: "Search",
        title: "SEO structure built in, not bolted on",
        description:
          "Every article includes structured headings, a meta description, and Schema.org JSON-LD. Content marketing for SaaS only pays off when posts actually rank; PersonnaPress is built with that constraint from the start.",
      },
    ],
    faqItems: [
      {
        question: "What is content marketing for SaaS and why does it matter?",
        answer:
          "Content marketing for SaaS is the practice of publishing SEO-targeted articles, guides, and tutorials that attract founders, developers, and buyers searching for solutions your product solves. Unlike paid acquisition, content compounds over time: a well-ranked article keeps bringing in trial sign-ups months or years after it was written. For SaaS founders with limited acquisition budgets, organic content is often the highest-ROI channel at scale.",
      },
      {
        question: "How is an AI blog writer different from a general AI writing tool for a SaaS founder?",
        answer:
          "A general AI writing tool generates text when you prompt it, but stops there. You still write the brief, review the draft, format it for SEO, copy it into your CMS, and post the social content manually. PersonnaPress is built as a complete publish loop: it learns your voice, structures content for SEO, and publishes the article and social posts to your blog and channels automatically after a single approval. For a solo founder or a small team, that difference means the difference between publishing consistently and publishing never.",
      },
      {
        question: "Can AI really write in my voice for long-form SaaS content?",
        answer:
          "Voice fidelity in short copy is easy; the challenge is holding it across 1,500 to 2,500 words. PersonnaPress trains on your own content samples to capture your specific vocabulary, sentence rhythm, and level of technical depth. The result reads like you wrote it, not like generic AI output. Readers who already know your writing consistently describe PersonnaPress output as sounding like the founder.",
      },
      {
        question: "What does 'content marketing for startups' look like with PersonnaPress?",
        answer:
          "For a startup, the goal is usually to rank for a handful of high-intent keywords before you can afford a content team. PersonnaPress lets you input a topic or a rough brain dump, then generates a keyword-targeted, SEO-structured article in your voice and publishes it to your blog and social channels. The workflow is: choose topic, review draft, approve. That's a realistic publishing cadence for a one-person founding team.",
      },
      {
        question: "Does PersonnaPress handle SaaS content writing end to end?",
        answer:
          "PersonnaPress covers the write-and-publish loop end to end: voice extraction, article generation, social post generation, and publishing to GitHub, WordPress, Webflow, or the headless delivery API, plus X, LinkedIn, and Meta. It doesn't handle keyword research or SERP analysis; you bring the topic, PersonnaPress handles the content and the distribution.",
      },
    ],
    relatedLinks: [
      { href: "/ai-content-for-coaches", label: "AI content for coaches" },
      { href: "/white-label-content-for-agencies", label: "White-label content for agencies" },
      { href: "/best-ai-blog-writers", label: "Best AI blog writers" },
      { href: "/jasper-alternatives", label: "Jasper alternatives" },
    ],
  },

  coaches: {
    slug: "ai-content-for-coaches",
    persona: "Coaches",
    primaryKeyword: "content marketing for coaches",
    metadata: {
      title: "AI Content Marketing for Coaches, in Your Own Voice",
      description:
        "PersonnaPress is the AI content tool built for coaches: it learns your voice from your own writing, generates articles and social posts that sound like you, and publishes automatically so you stay visible without ghostwriters.",
      canonicalPath: "/ai-content-for-coaches",
    },
    h1: "AI Content Marketing for Coaches, in Your Own Voice",
    breadcrumbLabel: "AI Content for Coaches",
    painsHeading: "Why your content backlog keeps growing",
    solutionsHeading: "The full publish loop, in your voice",
    heroAnswer:
      "The best AI content marketing tool for coaches is one that sounds like you, not like generic AI. PersonnaPress learns your coaching voice from your existing writing and creates blog articles and social posts that reflect your philosophy and style, then publishes them automatically so you stay consistently visible to the clients you want to reach.",
    pains: [
      {
        title: "You know what to say; finding time to write it is the problem",
        description:
          "Your methodology is clear. Your client results speak for themselves. But sitting down to write a 1,500-word article every week competes with actual coaching hours, and the content backlog keeps growing.",
      },
      {
        title: "Ghostwriters don't capture your coaching voice",
        description:
          "Hiring a writer means endless edits to put your philosophy back in. Clients who've read your content expect a specific voice and approach; content that misses it erodes trust before the first call.",
      },
      {
        title: "Posting consistently on social is its own full-time job",
        description:
          "An article sitting in a Google Doc helps no one. Turning it into LinkedIn posts, repurposed insights, and a consistent social presence requires a separate workflow that most coaches never build.",
      },
    ],
    solutions: [
      {
        iconName: "FileText",
        title: "Your voice, your philosophy, your words",
        description:
          "PersonnaPress reads your existing content to learn how you write: your frameworks, your preferred examples, your level of warmth or directness. Output reads like you wrote it, not like a template.",
      },
      {
        iconName: "Share2",
        title: "Blog and social in one workflow",
        description:
          "After you approve an article, PersonnaPress publishes it to your blog and generates LinkedIn, X, and Meta posts from the same piece. One approval, consistent presence across channels.",
      },
      {
        iconName: "RefreshCw",
        title: "Consistent publishing without consistent effort",
        description:
          "Drop a topic, a client question, or a framework you teach. PersonnaPress turns it into a full article and social posts. You review, approve, and it goes live. No more content backlogs.",
      },
    ],
    faqItems: [
      {
        question: "What is content marketing for coaches and why is it valuable?",
        answer:
          "Content marketing for coaches means publishing articles, guides, and social posts that demonstrate your methodology and attract clients who are already searching for the transformation you offer. Unlike paid ads, content builds trust over time: a client who has read five of your articles arrives on a discovery call already sold on your approach. For coaches whose business runs on relationship and credibility, organic content is one of the highest-leverage marketing channels available.",
      },
      {
        question: "How does PersonnaPress make sure my content sounds like me and not like generic AI?",
        answer:
          "PersonnaPress trains on samples of your existing writing: blog posts, email newsletters, social captions, or any text that captures your voice. It extracts your vocabulary, sentence rhythm, level of directness, and the frameworks you use. Every article it generates applies those patterns throughout the full piece, not just in the opening. Coaches who use PersonnaPress describe the output as immediately recognizable as their own voice, which means less editing and more trust from readers.",
      },
      {
        question: "Can AI write about my specific coaching methodology?",
        answer:
          "Yes. When you provide a topic or a description of the concept you want to cover, PersonnaPress uses that input alongside your voice profile to write an article grounded in your methodology. It won't invent client results or fabricate specific claims, but it will articulate your frameworks, your perspective on common coaching questions, and your approach to the outcomes your clients seek. You review and approve before anything publishes.",
      },
      {
        question: "How much time does it actually save compared to writing myself?",
        answer:
          "Writing a 1,500-word article from scratch typically takes two to four hours for a coach who knows their material well. With PersonnaPress, you spend five to ten minutes inputting a topic and reviewing the draft. The editing pass is lighter because the voice is already calibrated to yours. Most coaches using PersonnaPress report going from publishing once a month (or never) to publishing once or twice a week without it feeling like a second job.",
      },
      {
        question: "Does PersonnaPress publish to social media as well as my blog?",
        answer:
          "Yes. After you approve an article, PersonnaPress generates social posts for LinkedIn, X, and Meta from the same content and publishes them through your connected accounts. For coaches whose ideal clients spend time on LinkedIn especially, this means every article becomes a multi-touch presence across the platforms where your audience already is.",
      },
    ],
    relatedLinks: [
      { href: "/ai-blog-writer-for-saas-founders", label: "AI blog writer for SaaS founders" },
      { href: "/white-label-content-for-agencies", label: "White-label content for agencies" },
      { href: "/best-ai-blog-writers", label: "Best AI blog writers" },
      { href: "/brand-voice-generator", label: "Brand Voice Generator" },
    ],
  },

  agencies: {
    slug: "white-label-content-for-agencies",
    persona: "Agencies",
    primaryKeyword: "white label content creation",
    metadata: {
      title: "White-Label AI Blog Writing for Agencies, in Every Client's Voice",
      description:
        "PersonnaPress is the white-label AI blog writing platform built for agencies: one workspace per client, each with its own brand voice, publishing to the client's blog and social channels. Scale content delivery without scaling headcount.",
      canonicalPath: "/white-label-content-for-agencies",
    },
    h1: "White-Label AI Blog Writing for Agencies, in Every Client's Voice",
    breadcrumbLabel: "White-Label Content for Agencies",
    painsHeading: "Why content margins stay thin",
    solutionsHeading: "Multi-client voice delivery, at scale",
    heroAnswer:
      "The best white-label content creation tool for agencies is one that holds a distinct brand voice for every client account, not one voice averaged across all of them. PersonnaPress gives each client their own voice profile and publishes articles and social posts to their blog and channels automatically, so you scale content delivery without scaling your writing team.",
    pains: [
      {
        title: "Scaling content delivery means scaling headcount",
        description:
          "Adding a new content client usually means adding a writer, an editor, and a project manager. The margins stay thin because the work stays linear. There's no leverage in the model.",
      },
      {
        title: "Every client has a different voice and a different CMS",
        description:
          "A B2B SaaS client, a professional services firm, and an e-commerce brand all have different tones, different audiences, and different publishing setups. Managing that variety manually doesn't scale.",
      },
      {
        title: "Publishing is a separate handoff your clients don't love",
        description:
          "Delivering a Word document or a Google Doc and asking the client to publish it themselves creates friction, delays, and errors. Clients want content live on their site, not in a shared folder.",
      },
    ],
    solutions: [
      {
        iconName: "FileText",
        title: "A separate voice profile for every client",
        description:
          "Each client account in PersonnaPress has its own brand voice extracted from that client's existing content. Articles generated for Client A sound nothing like articles for Client B, because they're trained on entirely different voice profiles.",
      },
      {
        iconName: "RefreshCw",
        title: "Publish directly to the client's blog and channels",
        description:
          "Connect each client's GitHub, WordPress, Webflow, or headless CMS and their social accounts. When you approve an article, it publishes to their properties, not yours. White-label delivery, end to end.",
      },
      {
        iconName: "Share2",
        title: "Scale content without scaling your team",
        description:
          "PersonnaPress handles the write-and-publish loop for each client account. You review and approve. You can deliver consistent blog and social content for ten clients with the same team that used to serve three.",
      },
    ],
    faqItems: [
      {
        question: "What is white-label content creation and how does it work for agencies?",
        answer:
          "White-label content creation means an agency produces blog articles, social posts, and other content that publishes under the client's brand with no visible involvement from the agency or the tools it uses. For agencies, it means the client sees polished content appearing on their blog and social channels; they don't see the production workflow behind it. PersonnaPress enables this by publishing directly to each client's connected blog and social accounts, with articles written in that client's specific voice.",
      },
      {
        question: "How does PersonnaPress keep each client's voice separate?",
        answer:
          "Each client has a dedicated workspace in PersonnaPress with its own voice profile trained on that client's content samples. The voice extraction reads the client's existing articles, web copy, or emails and captures their vocabulary, tone, sentence structure, and level of formality. When you generate content for that client, the output applies only their profile. Client A's articles will not bleed into Client B's, even if both are in the same agency account.",
      },
      {
        question: "Can agencies publish directly to each client's blog without the client needing to log in?",
        answer:
          "Yes. Each client workspace connects to the client's publishing targets: GitHub, WordPress, Webflow, or the headless delivery API. When you approve content in PersonnaPress, it publishes to that client's blog automatically. The client doesn't need to touch a CMS or a publishing tool. They see the article go live. You manage the workflow.",
      },
      {
        question: "What does white-label blog writing cost compared to in-house writers?",
        answer:
          "A mid-market agency writer costs roughly $4,000 to $7,000 per month fully loaded. PersonnaPress Agency plan is $199 per month and covers the write-and-publish loop for multiple client accounts. The savings are significant, but the real leverage is that PersonnaPress scales linearly with content volume while headcount does not. Adding a new content client adds a new workspace, not a new hire.",
      },
      {
        question: "Does PersonnaPress support social publishing for agency clients?",
        answer:
          "Yes. Each client workspace can connect X, LinkedIn, and Meta accounts. When an article is approved, PersonnaPress generates social posts adapted for each platform and publishes them to the client's accounts. Agencies deliver blog content and social distribution in one workflow, which is a stronger service offering than article delivery alone.",
      },
    ],
    relatedLinks: [
      { href: "/ai-blog-writer-for-saas-founders", label: "AI blog writer for SaaS founders" },
      { href: "/ai-content-for-coaches", label: "AI content for coaches" },
      { href: "/best-ai-blog-writers", label: "Best AI blog writers" },
      { href: "/jasper-alternatives", label: "Jasper alternatives" },
    ],
  },
};

export function buildPersonaJsonLd(
  data: PersonaPageData,
  appUrl: string,
): {
  softwareApp: object;
  faq: object;
  breadcrumb: object;
} {
  const softwareApp = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "PersonnaPress",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    url: appUrl,
    description:
      "AI content platform that learns your brand voice and turns ideas into SEO-structured blog posts and social posts, then publishes to your blog and social channels automatically.",
    offers: [
      {
        "@type": "Offer",
        name: "Starter",
        price: "29",
        priceCurrency: "USD",
        priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
      },
      {
        "@type": "Offer",
        name: "Growth",
        price: "79",
        priceCurrency: "USD",
        priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
      },
      {
        "@type": "Offer",
        name: "Agency",
        price: "199",
        priceCurrency: "USD",
        priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
      },
    ],
  };

  const faq = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: data.faqItems.map(({ question, answer }) => ({
      "@type": "Question",
      name: question,
      acceptedAnswer: { "@type": "Answer", text: answer },
    })),
  };

  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: appUrl },
      {
        "@type": "ListItem",
        position: 2,
        name: data.breadcrumbLabel,
        item: `${appUrl}${data.metadata.canonicalPath}`,
      },
    ],
  };

  return { softwareApp, faq, breadcrumb };
}
