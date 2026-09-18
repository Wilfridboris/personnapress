import type { Metadata } from "next";
import { PERSONAS, buildPersonaJsonLd } from "@/components/marketing/personas.data";
import { PersonaPage } from "@/components/marketing/PersonaPage";

export const dynamic = "force-static";

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");
const data = PERSONAS["agencies"];
const { softwareApp, faq, breadcrumb } = buildPersonaJsonLd(data, APP_URL);

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
          alt: "White-label AI blog writing for agencies",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: data.metadata.title,
      description: data.metadata.description,
      images: [`${APP_URL}/images/PersonnaPress-opengraph.png`],
    },
  };
}

export default function WhiteLabelContentForAgenciesPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareApp).replace(/</g, "\\u003c") }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faq).replace(/</g, "\\u003c") }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb).replace(/</g, "\\u003c") }}
      />
      <PersonaPage data={data} />
    </>
  );
}
