import { type NextRequest, NextResponse } from "next/server";
import { randomBytes } from "crypto";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const clientId = searchParams.get("client_id");
  if (!clientId) {
    return NextResponse.json({ error: "Missing client_id" }, { status: 400 });
  }

  const threadsAppId = process.env.NEXT_PUBLIC_THREADS_APP_ID;
  if (!threadsAppId) {
    return NextResponse.json({ error: "Threads OAuth is not configured" }, { status: 500 });
  }

  const state = randomBytes(32).toString("hex");
  const cookieValue = JSON.stringify({ state, clientId });

  const authUrl = new URL("https://threads.net/oauth/authorize");
  authUrl.searchParams.set("client_id", threadsAppId);
  authUrl.searchParams.set("redirect_uri", `${APP_URL}/api/auth/threads/callback`);
  authUrl.searchParams.set("scope", "threads_basic,threads_content_publish,threads_manage_insights");
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("state", state);

  const response = NextResponse.redirect(authUrl.toString());
  response.cookies.set("oauth_state_threads", cookieValue, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
