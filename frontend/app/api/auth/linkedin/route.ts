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
  const orgPostingEnabled = process.env.NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED === "true";
  // Member scopes: identity + personal posting + personal-post analytics.
  // r_member_postAnalytics powers memberCreatorPostAnalytics (Story 25-2). It is requested now
  // even though member-metrics collection stays gated by LINKEDIN_MEMBER_METRICS_ENABLED, so the
  // analytics re-consent is a single grant and users don't have to reconnect twice.
  const memberScopes = "openid profile w_member_social r_member_postAnalytics";
  // Org scopes: rw_organization_admin (not read-only r_organization_admin) is what
  // organizationalEntityShareStatistics requires for org-page analytics (Story 25-1) per LinkedIn docs,
  // and it is a superset of the read access needed for posting.
  const orgScopes = "rw_organization_admin w_organization_social";
  const scope = orgPostingEnabled ? `${memberScopes} ${orgScopes}` : memberScopes;
  authUrl.searchParams.set("scope", scope);
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
