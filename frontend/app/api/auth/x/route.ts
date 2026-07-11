import { type NextRequest, NextResponse } from "next/server";
import { randomBytes, createHash } from "crypto";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

function buildXAuthUrl(codeChallenge: string, state: string): string {
  const clientId = process.env.NEXT_PUBLIC_X_CLIENT_ID;
  if (!clientId) {
    throw new Error("NEXT_PUBLIC_X_CLIENT_ID is not configured");
  }
  const params = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: `${APP_URL}/api/auth/x/callback`,
    scope: "tweet.read tweet.write users.read offline.access",
    state,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });
  return `https://twitter.com/i/oauth2/authorize?${params.toString()}`;
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const clientId = searchParams.get("client_id");
  if (!clientId) {
    return NextResponse.json({ error: "Missing client_id" }, { status: 400 });
  }

  const codeVerifier = randomBytes(32).toString("base64url");
  const codeChallenge = createHash("sha256").update(codeVerifier).digest("base64url");
  const state = randomBytes(32).toString("hex");

  let authUrl: string;
  try {
    authUrl = buildXAuthUrl(codeChallenge, state);
  } catch {
    return NextResponse.json({ error: "X OAuth is not configured" }, { status: 500 });
  }

  const returnTo = searchParams.get("return_to") ?? undefined;
  const cookieValue = JSON.stringify({ state, codeVerifier, clientId, ...(returnTo ? { returnTo } : {}) });
  const response = NextResponse.redirect(authUrl);
  response.cookies.set("oauth_state_x", cookieValue, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
