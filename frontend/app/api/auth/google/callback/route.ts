import { type NextRequest, NextResponse } from "next/server";

const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
const GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo";
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

const ALLOWED_REDIRECT_PATHS = new Set(["/onboarding", "/dashboard"]);

function safeRedirectPath(path: string | undefined | null): string {
  if (path && ALLOWED_REDIRECT_PATHS.has(path)) return path;
  return "/onboarding";
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const storedState = request.cookies.get("oauth_state")?.value;

  if (!code || !state || !storedState || state !== storedState) {
    return NextResponse.redirect(`${APP_URL}/register?error=oauth_failed&detail=state_mismatch`);
  }

  try {
    const tokenRes = await fetch(GOOGLE_TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code,
        client_id: process.env.GOOGLE_CLIENT_ID ?? "",
        client_secret: process.env.GOOGLE_CLIENT_SECRET ?? "",
        redirect_uri: `${APP_URL}/api/auth/google/callback`,
        grant_type: "authorization_code",
      }),
    });

    if (!tokenRes.ok) {
      const body = await tokenRes.text();
      return NextResponse.redirect(
        `${APP_URL}/register?error=oauth_failed&detail=token_exchange&msg=${encodeURIComponent(body.slice(0, 200))}`
      );
    }

    const tokenData = await tokenRes.json();
    const accessToken: string = tokenData.access_token;

    const userRes = await fetch(GOOGLE_USERINFO_URL, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (!userRes.ok) {
      return NextResponse.redirect(`${APP_URL}/register?error=oauth_failed&detail=userinfo`);
    }

    const profile = await userRes.json();

    const backendRes = await fetch(`${BACKEND_URL}/api/v1/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        google_sub: profile.sub,
        email: profile.email,
        email_verified: profile.email_verified ?? false,
      }),
    });

    if (!backendRes.ok) {
      const body = await backendRes.text();
      return NextResponse.redirect(
        `${APP_URL}/register?error=oauth_failed&detail=backend&msg=${encodeURIComponent(body.slice(0, 200))}`
      );
    }

    const setCookieHeader = backendRes.headers.get("set-cookie");
    const redirectPath = safeRedirectPath((await backendRes.json()).redirect_url);

    const response = NextResponse.redirect(`${APP_URL}${redirectPath}`);
    response.cookies.delete("oauth_state");
    if (setCookieHeader) {
      response.headers.append("set-cookie", setCookieHeader);
    }
    return response;
  } catch (err) {
    return NextResponse.redirect(
      `${APP_URL}/register?error=oauth_failed&detail=exception&msg=${encodeURIComponent(String(err).slice(0, 200))}`
    );
  }
}
