import { type NextRequest, NextResponse } from "next/server";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function clearCookieRedirect(url: string): NextResponse {
  const res = NextResponse.redirect(url);
  res.cookies.delete("oauth_state_linkedin");
  return res;
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  const cookieRaw = request.cookies.get("oauth_state_linkedin")?.value;
  let oauthState: { state: string; clientId: string } | null = null;
  if (cookieRaw) {
    try {
      oauthState = JSON.parse(cookieRaw) as { state: string; clientId: string };
    } catch {
      // malformed cookie — treat as missing
    }
  }

  const connectionsUrl = oauthState?.clientId
    ? `${APP_URL}/clients/${oauthState.clientId}/connections`
    : `${APP_URL}/clients`;

  if (error) {
    return clearCookieRedirect(
      `${connectionsUrl}?error=${encodeURIComponent(`LinkedIn authorization failed — ${errorDescription ?? error}. Please try connecting again.`)}`
    );
  }

  if (!oauthState || state !== oauthState.state) {
    return clearCookieRedirect(
      `${connectionsUrl}?error=${encodeURIComponent("Authorization failed — the request was tampered with. Please try connecting again.")}`
    );
  }

  try {
    const backendResp = await fetch(
      `${BACKEND_URL}/api/v1/clients/${oauthState.clientId}/connections/linkedin/callback`,
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
        `${connectionsUrl}?error=${encodeURIComponent(err?.error?.message ?? "LinkedIn connection failed. Please try again.")}`
      );
    }
  } catch {
    return clearCookieRedirect(
      `${connectionsUrl}?error=${encodeURIComponent("LinkedIn connection failed. Please try again.")}`
    );
  }

  return clearCookieRedirect(`${connectionsUrl}?success=linkedin`);
}
