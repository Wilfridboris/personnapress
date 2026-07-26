'use client';

import { useState } from 'react';
import { CheckCircle } from 'lucide-react';

export function EmailCaptureWidget({ source = 'homepage' }: { source?: string }) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('loading');
    setErrorMsg('');
    try {
      const res = await fetch('/api/email-capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source }),
      });
      // The API route already converts Resend 409 duplicates to 200.
      // Any remaining non-200 is a real error.
      if (!res.ok) throw new Error();
      setStatus('success');
    } catch {
      setStatus('error');
      setErrorMsg('Something went wrong. Please try again.');
    }
  }

  if (status === 'success') {
    return (
      <section aria-label="Newsletter signup" className="border-t border-border py-12 md:py-16">
        <div className="max-w-xl mx-auto px-4 text-center flex flex-col items-center gap-3 animate-fade-in-up">
          <CheckCircle className="size-8 text-success" aria-hidden="true" />
          <p className="font-body text-base text-ink">
            <span className="font-semibold">You&apos;re on the list.</span>{' '}
            We&apos;ll send your free Brand Voice Audit checklist shortly.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Newsletter signup" className="border-t border-border py-12 md:py-16">
      <div className="max-w-xl mx-auto px-4">
        <p className="font-body text-xs uppercase tracking-[0.06em] text-graphite mb-2">
          Free resource
        </p>
        <h2 className="font-display text-2xl md:text-3xl text-ink mb-2 text-balance">
          Get the free Brand Voice Audit checklist
        </h2>
        <p className="font-body text-sm text-graphite mb-8 text-pretty">
          12 questions to find your writing fingerprint. Stop your content from sounding like everyone else&apos;s.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col sm:flex-row sm:items-end gap-3 sm:gap-0">
            <div className="flex-1">
              <label htmlFor="email-capture-input" className="sr-only">
                Email address
              </label>
              <input
                id="email-capture-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={status === 'loading'}
                placeholder="Your email address"
                aria-invalid={status === 'error'}
                aria-describedby={status === 'error' ? 'email-capture-error' : undefined}
                className="w-full bg-transparent border-0 border-b-2 border-border px-0 py-2
                           font-body text-base text-ink placeholder:text-graphite
                           focus:outline-none focus:border-ink focus-visible:outline-none
                           transition-colors duration-150
                           disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            <button
              type="submit"
              disabled={status === 'loading'}
              aria-disabled={status === 'loading'}
              className="sm:ml-4 px-5 py-2 font-body text-sm font-semibold uppercase tracking-[0.06em]
                         bg-ink text-white border border-ink shadow-brutal
                         hover:bg-white hover:text-ink
                         transition-colors duration-150
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2
                         disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {status === 'loading' ? 'Sending…' : 'Get the checklist'}
            </button>
          </div>

          {status === 'error' && (
            <p
              id="email-capture-error"
              role="alert"
              className="mt-2 font-body text-sm text-danger animate-fade-in"
            >
              {errorMsg}
            </p>
          )}
        </form>
      </div>
    </section>
  );
}
