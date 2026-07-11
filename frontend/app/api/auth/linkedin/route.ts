import { type NextRequest, NextResponse } from "next/server";
import { randomBytes } from "crypto";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const clientId = searchParams.get("client_id");
  if (!clientId) {
    return NextResponse.json({ error: "Missing client_id" }, { status: 400 });
  }

  const linkedInClientId = process.env.NEXT_PUBLIC_LINKEDIN_CLIENT_ID;
  if (!linkedInClientId) {
    return NextResponse.json({ error: "LinkedIn OAuth is not configured" }, { status: 500 });
  }

  const state = randomBytes(32).toString("hex");
  const returnTo = searchParams.get("return_to") ?? undefined;
  const cookieValue = JSON.stringify({ state, clientId, ...(returnTo ? { returnTo } : {}) });

  const authUrl = new URL("https://www.linkedin.com/oauth/v2/authorization");
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("client_id", linkedInClientId);
  authUrl.searchParams.set("redirect_uri", `${APP_URL}/api/auth/linkedin/callback`);
  authUrl.searchParams.set("scope", "openid profile w_member_social");
  authUrl.searchParams.set("state", state);

  const response = NextResponse.redirect(authUrl.toString());
  response.cookies.set("oauth_state_linkedin", cookieValue, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
