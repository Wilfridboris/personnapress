import { type NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

if (!process.env.JWT_SECRET) {
  throw new Error("JWT_SECRET environment variable is required");
}
const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET);

export async function middleware(request: NextRequest) {
  const token = request.cookies.get("session")?.value;

  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const { payload } = await jwtVerify(token, JWT_SECRET);

    if (!payload.verified) {
      const url = new URL("/verify-email", request.url);
      if (payload.email && typeof payload.email === "string") {
        url.searchParams.set("email", payload.email);
      }
      return NextResponse.redirect(url);
    }

    return NextResponse.next();
  } catch {
    return NextResponse.redirect(new URL("/login", request.url));
  }
}

export const config = {
  matcher: [
    "/(dashboard|clients|campaigns|settings|onboarding)(.*)",
  ],
};
