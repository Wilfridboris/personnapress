import { type NextRequest, NextResponse } from "next/server";
import { randomBytes } from "crypto";

const APP_URL = (process.env.APP_URL ?? "http://localhost:3000").replace(/[./]+$/, "");

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const clientId = searchParams.get("client_id");
  if (!clientId) {
    return NextResponse.json({ error: "Missing client_id" }, { status: 400 });
  }

  const wpComClientId = process.env.WP_COM_CLIENT_ID;
  if (!wpComClientId) {
    return NextResponse.json({ error: "WordPress.com OAuth is not configured" }, { status: 500 });
  }

  const state = randomBytes(32).toString("hex");
  const returnTo = searchParams.get("return_to") ?? undefined;
  const redirectUri = `${APP_URL}/api/auth/wordpress-com/callback`;

  const params = new URLSearchParams({
    client_id: wpComClientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "global",
    state,
    // NOTE: "blog" param is intentionally omitted — passing "all" is invalid;
    // omitting it lets WordPress.com authorize access to all the user's blogs
  });

  const authUrl = `https://public-api.wordpress.com/oauth2/authorize?${params.toString()}`;

  const cookieValue = JSON.stringify({ state, clientId, ...(returnTo ? { returnTo } : {}) });
  const response = NextResponse.redirect(authUrl);
  response.cookies.set("oauth_state_wpcom", cookieValue, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
