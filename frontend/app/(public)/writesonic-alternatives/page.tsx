import type { Metadata } from "next";
import { COMPARISONS } from "@/components/marketing/comparisons.data";
import { ComparisonPage } from "@/components/marketing/ComparisonPage";

export const dynamic = "force-static";

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");
const data = COMPARISONS["writesonic"];

export function generateMetadata(): Metadata {
  return {
    title: { absolute: data.metadata.title },
    description: data.metadata.description,
    alternates: { canonical: `${APP_URL}${data.metadata.canonicalPath}` },
    openGraph: {
      title: data.metadata.title,
      description: data.metadata.description,
      type: "website",
      url: `${APP_URL}${data.metadata.canonicalPath}`,
      images: [
        {
          url: "/images/PersonnaPress-opengraph.png",
          width: 1200,
          height: 630,
          alt: "PersonnaPress vs Writesonic comparison",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: data.metadata.title,
      description: data.metadata.description,
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

const jsonLdFaq = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: data.faqItems.map(({ question, answer }) => ({
    "@type": "Question",
    name: question,
    acceptedAnswer: { "@type": "Answer", text: answer },
  })),
};

const jsonLdBreadcrumb = {
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    { "@type": "ListItem", position: 1, name: "Home", item: APP_URL },
    {
      "@type": "ListItem",
      position: 2,
      name: data.metadata.title.split(" | ")[0],
      item: `${APP_URL}${data.metadata.canonicalPath}`,
    },
  ],
};

export default function WritesonicAlternativesPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdSoftwareApp).replace(/</g, "\\u003c") }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdFaq).replace(/</g, "\\u003c") }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdBreadcrumb).replace(/</g, "\\u003c") }}
      />
      <ComparisonPage data={data} />
    </>
  );
}
