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
  metadataBase: new URL("https://personapress.io"),
  title: {
    default: "PersonaPress - Publish in Your Voice, Not AI's",
    template: "%s | PersonaPress",
  },
  description:
    "PersonaPress turns your raw ideas into SEO-ranked blog posts and social campaigns that sound exactly like you. Built for founders, coaches, and agencies.",
  keywords: [
    "AI content writing",
    "blog automation",
    "content marketing",
    "social media automation",
    "SEO blog posts",
    "brand voice AI",
  ],
  openGraph: {
    title: "PersonaPress - Publish in Your Voice, Not AI's",
    description:
      "Turn your brain dumps into published, ranked content. Your voice, your style, every time.",
    type: "website",
    locale: "en_US",
    siteName: "PersonaPress",
  },
  twitter: {
    card: "summary_large_image",
    title: "PersonaPress",
    description: "AI content that sounds like you, published and ranked.",
  },
  robots: {
    index: true,
    follow: true,
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
