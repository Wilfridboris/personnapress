import { type NextRequest, NextResponse } from "next/server";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function clearCookieRedirect(url: string): NextResponse {
  const res = NextResponse.redirect(url);
  res.cookies.delete("oauth_state_x");
  return res;
}

type XOAuthState = { state: string; codeVerifier: string; clientId: string; returnTo?: string };

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  const cookieRaw = request.cookies.get("oauth_state_x")?.value;
  let oauthState: XOAuthState | null = null;
  if (cookieRaw) {
    try {
      oauthState = JSON.parse(cookieRaw) as XOAuthState;
    } catch {
      // malformed cookie — treat as missing
    }
  }

  const connectionsUrl = oauthState?.clientId
    ? `${APP_URL}/clients/${oauthState.clientId}/connections`
    : `${APP_URL}/clients`;

  // Handle provider error and CSRF check before trusting the cookie's returnTo field
  if (error) {
    return clearCookieRedirect(
      `${connectionsUrl}?error=${encodeURIComponent(`X authorization failed — ${errorDescription ?? error}. Please try connecting again.`)}`
    );
  }

  if (!oauthState || state !== oauthState.state) {
    return clearCookieRedirect(
      `${connectionsUrl}?error=${encodeURIComponent("Authorization failed — the request was tampered with. Please try connecting again.")}`
    );
  }

  // State validated — cookie is trusted; derive onboarding redirect targets
  const isOnboarding = oauthState.returnTo === "onboarding";
  const successUrl = isOnboarding ? `${APP_URL}/onboarding?success=x` : `${connectionsUrl}?success=x`;
  const errorBase = isOnboarding ? `${APP_URL}/onboarding` : connectionsUrl;

  try {
    const backendResp = await fetch(
      `${BACKEND_URL}/api/v1/clients/${oauthState.clientId}/connections/x/callback`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: request.headers.get("cookie") ?? "",
        },
        body: JSON.stringify({ code, code_verifier: oauthState.codeVerifier }),
      }
    );

    if (!backendResp.ok) {
      const err = await backendResp.json().catch(() => ({})) as { error?: { message?: string } };
      return clearCookieRedirect(
        `${errorBase}?error=${encodeURIComponent(err?.error?.message ?? "X connection failed. Please try again.")}`
      );
    }
  } catch {
    return clearCookieRedirect(
      `${errorBase}?error=${encodeURIComponent("X connection failed. Please try again.")}`
    );
  }

  return clearCookieRedirect(successUrl);
}
