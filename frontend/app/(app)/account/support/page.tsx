import type { Metadata } from "next";
import { Mail, ArrowUpRight } from "lucide-react";

export const metadata: Metadata = {
  title: "Help & Support | PersonnaPress",
  robots: { index: false },
};

const QUICK_ACTIONS = [
  { label: "Request Beta Access", subject: "Beta%20Access%20Request%20-%20PersonnaPress" },
  { label: "Report a Bug", subject: "Bug%20Report%20-%20PersonnaPress" },
  { label: "Feature Request", subject: "Feature%20Request%20-%20PersonnaPress" },
  { label: "Billing Question", subject: "Billing%20Question%20-%20PersonnaPress" },
] as const;

export default function SupportPage() {
  return (
    <div className="max-w-lg">
      <h1 className="font-display text-3xl text-ink">Help &amp; Support</h1>

      <hr className="border-[#E5E5E5] my-6" />

      <section>
        <p className="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-2">
          Contact
        </p>
        <a
          href="mailto:support@personnapress.com"
          className="font-body text-sm text-ink underline underline-offset-2 hover:text-graphite transition-colors"
        >
          support@personnapress.com
        </a>
        <p className="font-body text-xs text-graphite mt-1">
          We typically respond within 24 hours on business days.
        </p>
      </section>

      <hr className="border-[#E5E5E5] my-6" />

      <section>
        <p className="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-3">
          Quick requests
        </p>
        <p className="font-body text-sm text-graphite mb-4">
          Tap to open a pre-filled email for common requests.
        </p>
        <div className="space-y-2">
          {QUICK_ACTIONS.map(({ label, subject }) => (
            <a
              key={subject}
              href={`mailto:support@personnapress.com?subject=${subject}`}
              className="flex items-center gap-3 w-full px-4 min-h-[44px] border border-[#E5E5E5] bg-white text-[#111111] text-sm hover:bg-[#F9F9F6] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
            >
              <Mail className="size-4 shrink-0 text-[#555555]" aria-hidden="true" />
              <span className="flex-1">{label}</span>
              <ArrowUpRight className="size-3.5 shrink-0 text-[#555555]" aria-hidden="true" />
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
