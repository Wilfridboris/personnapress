import { type NextRequest, NextResponse } from "next/server";
import { randomBytes } from "crypto";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";
const GITHUB_APP_SLUG = process.env.GITHUB_APP_SLUG ?? "";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const clientId = searchParams.get("client_id");
  if (!clientId) {
    return NextResponse.json({ error: "Missing client_id" }, { status: 400 });
  }
  if (!GITHUB_APP_SLUG) {
    return NextResponse.json({ error: "GitHub App is not configured" }, { status: 500 });
  }

  const state = randomBytes(32).toString("hex");
  const installUrl = `https://github.com/apps/${GITHUB_APP_SLUG}/installations/new?state=${state}`;

  const cookieValue = JSON.stringify({ state, clientId });
  const response = NextResponse.redirect(installUrl);
  response.cookies.set("github_oauth_state", cookieValue, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
