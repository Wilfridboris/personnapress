import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("crypto", async (importOriginal) => {
  const actual = await importOriginal<typeof import("crypto")>();
  return {
    ...actual,
    randomBytes: vi.fn(() => Buffer.from("aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899", "hex")),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
  process.env.NEXT_PUBLIC_X_CLIENT_ID = "test-x-client-id";
  process.env.APP_URL = "http://localhost:3000";
});

describe("GET /api/auth/x (initiation)", () => {
  it("returns 400 when client_id is missing", async () => {
    const { GET } = await import("@/app/api/auth/x/route");
    const req = new NextRequest("http://localhost:3000/api/auth/x");
    const res = await GET(req);
    expect(res.status).toBe(400);
  });

  it("sets httpOnly oauth_state_x cookie with state + codeVerifier + clientId", async () => {
    const { GET } = await import("@/app/api/auth/x/route");
    const req = new NextRequest("http://localhost:3000/api/auth/x?client_id=abc-123");
    const res = await GET(req);
    expect(res.status).toBe(307);
    const setCookie = res.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain("oauth_state_x=");
    expect(setCookie).toContain("HttpOnly");
    expect(setCookie.toLowerCase()).toContain("samesite=lax");
    const match = setCookie.match(/oauth_state_x=([^;]+)/);
    const cookie = JSON.parse(decodeURIComponent(match![1]));
    expect(cookie.clientId).toBe("abc-123");
    expect(typeof cookie.state).toBe("string");
    expect(typeof cookie.codeVerifier).toBe("string");
  });

  it("redirects to Twitter OAuth authorization URL", async () => {
    const { GET } = await import("@/app/api/auth/x/route");
    const req = new NextRequest("http://localhost:3000/api/auth/x?client_id=abc-123");
    const res = await GET(req);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("twitter.com/i/oauth2/authorize");
    expect(location).toContain("code_challenge_method=S256");
    expect(location).toContain("scope=");
  });
});

describe("GET /api/auth/x/callback — CSRF mismatch", () => {
  it("redirects with tampered error when state does not match", async () => {
    const { GET } = await import("@/app/api/auth/x/callback/route");
    const cookieValue = JSON.stringify({ state: "correct-state", codeVerifier: "ver", clientId: "client-1" });
    const req = new NextRequest(
      "http://localhost:3000/api/auth/x/callback?code=abc&state=wrong-state",
      { headers: { cookie: `oauth_state_x=${encodeURIComponent(cookieValue)}` } }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("error=");
    expect(decodeURIComponent(location)).toContain("tampered");
  });

  it("redirects with error when oauth_state_x cookie is missing", async () => {
    const { GET } = await import("@/app/api/auth/x/callback/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/x/callback?code=abc&state=some-state"
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("error=");
    expect(decodeURIComponent(location)).toContain("tampered");
  });

  it("redirects with error when oauth_state_x cookie is malformed JSON", async () => {
    const { GET } = await import("@/app/api/auth/x/callback/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/x/callback?code=abc&state=some-state",
      { headers: { cookie: "oauth_state_x=not-valid-json" } }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("error=");
    expect(decodeURIComponent(location)).toContain("tampered");
  });
});
