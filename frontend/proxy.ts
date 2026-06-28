import { jwtVerify } from "jose";
import { NextRequest, NextResponse } from "next/server";

if (!process.env.JWT_SECRET) {
  throw new Error("JWT_SECRET environment variable is required");
}
const secret = new TextEncoder().encode(process.env.JWT_SECRET);

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublicRoute =
    pathname.startsWith("/login") ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/verify-email") ||
    pathname.startsWith("/api/auth/") ||
    pathname.startsWith("/api/webhooks/");

  const sessionCookie = request.cookies.get("session")?.value;

  if (!isPublicRoute) {
    if (!sessionCookie) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    try {
      const { payload } = await jwtVerify(sessionCookie, secret);
      if (!payload.verified) {
        return NextResponse.redirect(new URL("/verify-email", request.url));
      }
      const requestHeaders = new Headers(request.headers);
      requestHeaders.set("x-user-id", payload.user_id as string);
      requestHeaders.set("x-plan-tier", payload.plan_tier as string);
      return NextResponse.next({ request: { headers: requestHeaders } });
    } catch {
      const response = NextResponse.redirect(new URL("/login", request.url));
      response.cookies.delete("session");
      return response;
    }
  }

  if ((pathname === "/login" || pathname === "/register") && sessionCookie) {
    try {
      await jwtVerify(sessionCookie, secret);
      return NextResponse.redirect(new URL("/dashboard", request.url));
    } catch {
      // expired or invalid — let them see the auth page
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|public/).*)"],
};
