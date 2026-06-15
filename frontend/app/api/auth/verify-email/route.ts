import { type NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (!token) {
    return NextResponse.json(
      { detail: { error: { code: "MISSING_TOKEN", message: "Missing verification token." } } },
      { status: 400 }
    );
  }

  const backendRes = await fetch(
    `${BACKEND_URL}/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`
  );

  const data = await backendRes.json();

  if (!backendRes.ok) {
    return NextResponse.json(data, { status: backendRes.status });
  }

  const setCookieHeader = backendRes.headers.get("set-cookie");
  const response = NextResponse.json(data, { status: 200 });
  if (setCookieHeader) {
    response.headers.append("set-cookie", setCookieHeader);
  }
  return response;
}
