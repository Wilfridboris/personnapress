import type { Metadata } from "next";
import { Playfair_Display, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: "700",
  display: "swap",
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com"),
  title: {
    default: "PersonnaPress - Publish in Your Voice, Not AI's",
    template: "%s | PersonnaPress",
  },
  description:
    "PersonnaPress turns your raw ideas into SEO-ranked blog posts and social campaigns that sound exactly like you. Built for founders, coaches, and agencies.",
  keywords: [
    "AI content writing",
    "blog automation",
    "content marketing automation",
    "social media automation",
    "SEO blog posts",
    "brand voice AI",
    "AI writing tool",
    "content agency tool",
    "WordPress publishing automation",
    "LinkedIn content automation",
  ],
  manifest: "/site.webmanifest",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/icon.png", type: "image/png" },
    ],
    apple: "/apple-icon.png",
    shortcut: "/favicon.ico",
  },
  openGraph: {
    title: "PersonnaPress - Publish in Your Voice, Not AI's",
    description:
      "Turn your brain dumps into published, ranked content. Your voice, your style, every time.",
    type: "website",
    locale: "en_US",
    siteName: "PersonnaPress",
    images: [
      {
        url: "/images/PersonnaPress-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PersonnaPress - AI content engine that publishes in your voice",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "PersonnaPress - Publish in Your Voice, Not AI's",
    description: "AI content that sounds like you, published and ranked.",
    images: ["/images/PersonnaPress-opengraph.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-paper text-ink font-body">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
