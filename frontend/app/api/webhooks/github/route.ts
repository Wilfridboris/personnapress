export async function POST(request: Request) {
  const body = await request.text();
  const sigHeader = request.headers.get("x-hub-signature-256") ?? "";
  const eventType = request.headers.get("x-github-event") ?? "";

  const apiUrl =
    process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const res = await fetch(`${apiUrl}/api/v1/webhooks/github`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-hub-signature-256": sigHeader,
      "x-github-event": eventType,
    },
    body,
  });

  return new Response(res.ok ? "OK" : "Upstream error", {
    status: res.ok ? 200 : (res.status >= 400 && res.status < 500 ? res.status : 500),
  });
}
