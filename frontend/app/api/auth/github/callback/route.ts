import { type NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const state = searchParams.get("state");
  const installationId = searchParams.get("installation_id");

  const rawCookie = request.cookies.get("github_oauth_state")?.value;
  if (!rawCookie || !state || !installationId) {
    return NextResponse.redirect(`${APP_URL}/dashboard?error=${encodeURIComponent("GitHub connection failed.")}`);
  }

  if (!/^\d+$/.test(installationId)) {
    return NextResponse.redirect(`${APP_URL}/dashboard?error=${encodeURIComponent("GitHub connection failed.")}`);
  }

  let cookieData: { state: string; clientId: string };
  try {
    cookieData = JSON.parse(rawCookie);
  } catch {
    return NextResponse.redirect(`${APP_URL}/dashboard?error=${encodeURIComponent("GitHub connection failed.")}`);
  }

  if (!cookieData.state || !cookieData.clientId) {
    return NextResponse.redirect(`${APP_URL}/dashboard?error=${encodeURIComponent("GitHub connection failed.")}`);
  }

  if (cookieData.state !== state) {
    return NextResponse.redirect(`${APP_URL}/dashboard?error=${encodeURIComponent("GitHub connection failed.")}`);
  }

  const { clientId } = cookieData;
  if (!UUID_RE.test(clientId)) {
    return NextResponse.redirect(`${APP_URL}/dashboard?error=${encodeURIComponent("GitHub connection failed.")}`);
  }

  const connectionsUrl = `${APP_URL}/clients/${clientId}/connections`;

  try {
    const sessionCookie = request.cookies.get("session")?.value;
    const backendRes = await fetch(
      `${BACKEND_URL}/api/v1/clients/${clientId}/connections/github`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(sessionCookie ? { Cookie: `session=${sessionCookie}` } : {}),
        },
        body: JSON.stringify({ installation_id: installationId }),
      }
    );

    if (!backendRes.ok) {
      const response = NextResponse.redirect(`${connectionsUrl}?error=${encodeURIComponent("GitHub connection failed.")}`);
      response.cookies.delete("github_oauth_state");
      return response;
    }
  } catch {
    const response = NextResponse.redirect(`${connectionsUrl}?error=${encodeURIComponent("GitHub connection failed.")}`);
    response.cookies.delete("github_oauth_state");
    return response;
  }

  const response = NextResponse.redirect(`${connectionsUrl}?success=github`);
  response.cookies.delete("github_oauth_state");
  return response;
}
