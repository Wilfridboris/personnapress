import { ImageResponse } from "next/og";

export const alt = "Dark background with white headline reading 'AI Blog Writer for GitHub Pages' and framework names Jekyll, Astro, Hugo, Next.js, Eleventy listed below";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function GitHubPublisherOgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#111111",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "80px",
          fontFamily: "Georgia, serif",
        }}
      >
        <div
          style={{
            fontSize: "22px",
            color: "rgba(255,255,255,0.5)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            marginBottom: "24px",
            fontFamily: "monospace",
          }}
        >
          PersonnaPress
        </div>
        <div
          style={{
            fontSize: "56px",
            fontWeight: 700,
            color: "#ffffff",
            textAlign: "center",
            lineHeight: 1.2,
            maxWidth: "900px",
          }}
        >
          AI Blog Writer for GitHub Pages
        </div>
        <div
          style={{
            marginTop: "32px",
            fontSize: "24px",
            color: "rgba(255,255,255,0.6)",
            textAlign: "center",
            maxWidth: "700px",
            fontFamily: "sans-serif",
          }}
        >
          Jekyll · Astro · Hugo · Next.js · Eleventy
        </div>
        <div
          style={{
            marginTop: "48px",
            background: "#ffffff",
            color: "#111111",
            fontSize: "18px",
            fontWeight: 600,
            padding: "12px 32px",
            fontFamily: "sans-serif",
          }}
        >
          personnapress.com/github-publisher
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
