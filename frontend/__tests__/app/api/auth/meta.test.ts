import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("crypto", async (importOriginal) => {
  const actual = await importOriginal<typeof import("crypto")>();
  return {
    ...actual,
    randomBytes: vi.fn(() =>
      Buffer.from(
        "deadbeefcafe00112233445566778899deadbeefcafe00112233445566778899",
        "hex"
      )
    ),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
  process.env.NEXT_PUBLIC_META_APP_ID = "test-meta-app-id";
  process.env.APP_URL = "http://localhost:3000";
  process.env.BACKEND_URL = "http://localhost:8000";
});

// ── GET /api/auth/meta (OAuth initiation) ─────────────────────────────────────

describe("GET /api/auth/meta (initiation)", () => {
  it("returns 400 when client_id is missing", async () => {
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest("http://localhost:3000/api/auth/meta");
    const res = await GET(req);
    expect(res.status).toBe(400);
  });

  it("returns 500 when NEXT_PUBLIC_META_APP_ID is not configured", async () => {
    delete process.env.NEXT_PUBLIC_META_APP_ID;
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta?client_id=client-abc"
    );
    const res = await GET(req);
    expect(res.status).toBe(500);
  });

  it("sets httpOnly oauth_state_meta cookie with state and clientId", async () => {
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta?client_id=client-abc"
    );
    const res = await GET(req);
    expect(res.status).toBe(307);

    const setCookie = res.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain("oauth_state_meta=");
    expect(setCookie).toContain("HttpOnly");
    expect(setCookie.toLowerCase()).toContain("samesite=lax");
    expect(setCookie).toContain("Max-Age=600");

    const match = setCookie.match(/oauth_state_meta=([^;]+)/);
    const cookie = JSON.parse(decodeURIComponent(match![1]));
    expect(cookie.clientId).toBe("client-abc");
    expect(typeof cookie.state).toBe("string");
    expect(cookie.state.length).toBeGreaterThan(0);
  });

  it("redirects to facebook.com/v25.0/dialog/oauth", async () => {
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta?client_id=client-abc"
    );
    const res = await GET(req);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("facebook.com/v25.0/dialog/oauth");
  });

  it("redirect URL includes all required Meta scopes", async () => {
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta?client_id=client-abc"
    );
    const res = await GET(req);
    const location = decodeURIComponent(res.headers.get("location") ?? "");
    expect(location).toContain("instagram_basic");
    expect(location).toContain("instagram_content_publish");
    expect(location).toContain("pages_show_list");
    expect(location).toContain("pages_read_engagement");
    expect(location).toContain("pages_manage_posts");
    expect(location).toContain("threads_basic");
    expect(location).toContain("threads_content_publish");
  });

  it("redirect URL includes correct redirect_uri pointing to callback", async () => {
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta?client_id=client-abc"
    );
    const res = await GET(req);
    const location = decodeURIComponent(res.headers.get("location") ?? "");
    expect(location).toContain("redirect_uri=http://localhost:3000/api/auth/meta/callback");
  });

  it("redirect URL sets response_type=code", async () => {
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta?client_id=client-abc"
    );
    const res = await GET(req);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("response_type=code");
  });

  it("cookie state value matches the state in redirect URL", async () => {
    const { GET } = await import("@/app/api/auth/meta/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta?client_id=client-abc"
    );
    const res = await GET(req);

    const setCookie = res.headers.get("set-cookie") ?? "";
    const cookieMatch = setCookie.match(/oauth_state_meta=([^;]+)/);
    const cookie = JSON.parse(decodeURIComponent(cookieMatch![1]));

    const location = decodeURIComponent(res.headers.get("location") ?? "");
    expect(location).toContain(`state=${cookie.state}`);
  });
});

// ── GET /api/auth/meta/callback ────────────────────────────────────────────────

describe("GET /api/auth/meta/callback — CSRF and provider errors", () => {
  it("redirects with tampered error when state does not match cookie", async () => {
    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const cookieValue = JSON.stringify({
      state: "correct-state",
      clientId: "client-1",
    });
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta/callback?code=abc&state=wrong-state",
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("error=");
    expect(decodeURIComponent(location)).toContain("tampered");
  });

  it("redirects with tampered error when oauth_state_meta cookie is missing", async () => {
    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta/callback?code=abc&state=some-state"
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("error=");
    expect(decodeURIComponent(location)).toContain("tampered");
  });

  it("redirects with tampered error when oauth_state_meta cookie is malformed JSON", async () => {
    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta/callback?code=abc&state=some-state",
      { headers: { cookie: "oauth_state_meta=not-valid-json" } }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("error=");
    expect(decodeURIComponent(location)).toContain("tampered");
  });

  it("redirects with provider error when ?error param is present", async () => {
    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const cookieValue = JSON.stringify({
      state: "some-state",
      clientId: "client-1",
    });
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta/callback?error=access_denied&error_description=User+denied",
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = decodeURIComponent(res.headers.get("location") ?? "");
    expect(location).toContain("error=");
    expect(location).toContain("Meta authorization failed");
  });

  it("clears oauth_state_meta cookie on CSRF failure", async () => {
    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const cookieValue = JSON.stringify({
      state: "correct-state",
      clientId: "client-1",
    });
    const req = new NextRequest(
      "http://localhost:3000/api/auth/meta/callback?code=abc&state=wrong-state",
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    const res = await GET(req);
    const setCookie = res.headers.get("set-cookie") ?? "";
    // Cookie cleared: Max-Age=0 or empty value
    expect(setCookie.toLowerCase()).toMatch(/oauth_state_meta=;|max-age=0/);
  });
});

describe("GET /api/auth/meta/callback — success path", () => {
  it("redirects to connections page with ?success=meta on backend success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
    );

    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const state = "valid-state-abc";
    const cookieValue = JSON.stringify({ state, clientId: "client-1" });
    const req = new NextRequest(
      `http://localhost:3000/api/auth/meta/callback?code=auth-code-xyz&state=${state}`,
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toContain("success=meta");
  });

  it("POSTs code to correct backend endpoint on success", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", mockFetch);

    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const state = "valid-state-abc";
    const cookieValue = JSON.stringify({ state, clientId: "client-1" });
    const req = new NextRequest(
      `http://localhost:3000/api/auth/meta/callback?code=auth-code-xyz&state=${state}`,
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    await GET(req);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/clients/client-1/connections/meta/callback"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ code: "auth-code-xyz" }),
      })
    );
  });

  it("redirects with error when backend returns non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: { error: { message: "Meta token invalid" } } }),
      })
    );

    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const state = "valid-state-abc";
    const cookieValue = JSON.stringify({ state, clientId: "client-1" });
    const req = new NextRequest(
      `http://localhost:3000/api/auth/meta/callback?code=auth-code-xyz&state=${state}`,
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = decodeURIComponent(res.headers.get("location") ?? "");
    expect(location).toContain("error=");
    expect(location).toContain("Meta token invalid");
  });

  it("redirects with generic error when backend fetch throws", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Network failure"))
    );

    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const state = "valid-state-abc";
    const cookieValue = JSON.stringify({ state, clientId: "client-1" });
    const req = new NextRequest(
      `http://localhost:3000/api/auth/meta/callback?code=auth-code-xyz&state=${state}`,
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    const res = await GET(req);
    expect(res.status).toBe(307);
    const location = decodeURIComponent(res.headers.get("location") ?? "");
    expect(location).toContain("error=");
    expect(location).toContain("Meta connection failed");
  });

  it("clears oauth_state_meta cookie on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
    );

    const { GET } = await import("@/app/api/auth/meta/callback/route");
    const state = "valid-state-abc";
    const cookieValue = JSON.stringify({ state, clientId: "client-1" });
    const req = new NextRequest(
      `http://localhost:3000/api/auth/meta/callback?code=auth-code-xyz&state=${state}`,
      {
        headers: {
          cookie: `oauth_state_meta=${encodeURIComponent(cookieValue)}`,
        },
      }
    );
    const res = await GET(req);
    const setCookie = res.headers.get("set-cookie") ?? "";
    expect(setCookie.toLowerCase()).toMatch(/oauth_state_meta=;|max-age=0/);
  });
});
