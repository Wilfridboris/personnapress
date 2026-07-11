import { type NextRequest, NextResponse } from "next/server";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function clearCookieRedirect(url: string): NextResponse {
  const res = NextResponse.redirect(url);
  res.cookies.delete("oauth_state_wpcom");
  return res;
}

type WpComOAuthState = { state: string; clientId: string; returnTo?: string };

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  const cookieRaw = request.cookies.get("oauth_state_wpcom")?.value;
  let oauthState: WpComOAuthState | null = null;
  if (cookieRaw) {
    try {
      oauthState = JSON.parse(cookieRaw) as WpComOAuthState;
    } catch {
      // malformed cookie
    }
  }

  // Handle OAuth provider error before state check — returnTo not yet validated, use safe fallback
  if (error) {
    const errorUrl = oauthState?.clientId
      ? `${APP_URL}/clients/${oauthState.clientId}/connections`
      : `${APP_URL}/clients`;
    return clearCookieRedirect(
      `${errorUrl}?error=${encodeURIComponent(`WordPress.com authorization failed — ${error}. Please try connecting again.`)}`
    );
  }

  // Validate state — redirect to safe /clients fallback to prevent open redirect on tampered cookie
  if (!oauthState || state !== oauthState.state) {
    return clearCookieRedirect(
      `${APP_URL}/clients?error=${encodeURIComponent("Authorization failed — the request was tampered with. Please try connecting again.")}`
    );
  }

  // State validated — clientId and returnTo from cookie are trusted
  const connectionsUrl = `${APP_URL}/clients/${oauthState.clientId}/connections`;
  const isOnboarding = oauthState.returnTo === "onboarding";
  const successUrl = isOnboarding ? `${APP_URL}/onboarding?success=wordpress` : `${connectionsUrl}?success=wordpress-com`;
  const errorBase = isOnboarding ? `${APP_URL}/onboarding` : connectionsUrl;

  // Guard missing code (WP.com redirected without code and without error)
  if (!code) {
    return clearCookieRedirect(
      `${errorBase}?error=${encodeURIComponent("WordPress.com authorization failed — no authorization code received. Please try connecting again.")}`
    );
  }

  try {
    const backendResp = await fetch(
      `${BACKEND_URL}/api/v1/clients/${oauthState.clientId}/connections/wordpress-com/callback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: request.headers.get("cookie") ?? "",
        },
        body: JSON.stringify({ code }),
      }
    );

    if (!backendResp.ok) {
      const err = await backendResp.json().catch(() => ({})) as { error?: { message?: string } };
      return clearCookieRedirect(
        `${errorBase}?error=${encodeURIComponent(err?.error?.message ?? "WordPress.com connection failed. Please try again.")}`
      );
    }
  } catch {
    return clearCookieRedirect(
      `${errorBase}?error=${encodeURIComponent("WordPress.com connection failed. Please try again.")}`
    );
  }

  return clearCookieRedirect(successUrl);
}
