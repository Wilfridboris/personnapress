import { NextRequest, NextResponse } from 'next/server';
import { Resend } from 'resend';

const RESEND_API_KEY = process.env.RESEND_API_KEY?.trim();
const RESEND_AUDIENCE_ID = process.env.RESEND_AUDIENCE_ID?.trim();

// Module-level singleton — avoids re-initialising on every request
const resend = RESEND_API_KEY ? new Resend(RESEND_API_KEY) : null;

// Simple in-memory rate limiter (per-process): 5 requests / IP / minute
const _rateMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 5;
const RATE_WINDOW_MS = 60_000;

function _allow(ip: string): boolean {
  const now = Date.now();
  const entry = _rateMap.get(ip);
  if (!entry || entry.resetAt <= now) {
    _rateMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
    return true;
  }
  if (entry.count >= RATE_LIMIT) return false;
  entry.count++;
  return true;
}

const VALID_SOURCES = new Set(['homepage', 'pricing', 'about', 'blog', 'unknown']);

export async function POST(req: NextRequest) {
  if (!RESEND_API_KEY || !RESEND_AUDIENCE_ID || !resend) {
    console.warn('[email-capture] Missing RESEND_API_KEY or RESEND_AUDIENCE_ID');
    return NextResponse.json({ error: 'Service unavailable' }, { status: 500 });
  }

  const ip =
    req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? 'unknown';
  if (!_allow(ip)) {
    return NextResponse.json({ error: 'Too many requests' }, { status: 429 });
  }

  let email: string;
  let source: string;
  try {
    const body: unknown = await req.json();
    if (!body || typeof body !== 'object' || Array.isArray(body)) {
      return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
    }
    const b = body as Record<string, unknown>;
    email = String(b.email ?? '').trim().toLowerCase();
    const rawSource = String(b.source ?? 'unknown').trim().slice(0, 64);
    source = VALID_SOURCES.has(rawSource) ? rawSource : 'unknown';
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: 'Invalid email address' }, { status: 422 });
  }

  try {
    await resend.contacts.create({
      audienceId: RESEND_AUDIENCE_ID,
      email,
      unsubscribed: false,
      firstName: undefined,
      lastName: undefined,
    });
    return NextResponse.json({ subscribed: true });
  } catch (err: unknown) {
    const status =
      err != null && typeof err === 'object'
        ? ((err as { statusCode?: number }).statusCode ?? 0)
        : 0;
    // 409: contact already exists — treat as success per AC5
    if (status === 409) {
      return NextResponse.json({ subscribed: true });
    }
    if (status === 429) {
      return NextResponse.json({ error: 'Too many requests' }, { status: 429 });
    }
    console.error('[email-capture] Resend error:', err);
    return NextResponse.json({ error: 'Service error' }, { status: 500 });
  }
}
