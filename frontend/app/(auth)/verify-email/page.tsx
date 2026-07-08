import type { Metadata } from "next";
import { VerifyEmailClient } from "./VerifyEmailClient";

export const metadata: Metadata = {
  title: "Verify your email | PersonnaPress",
};

interface Props {
  searchParams: Promise<{ email?: string }>;
}

export default async function VerifyEmailPage({ searchParams }: Props) {
  const { email } = await searchParams;
  return (
    <div className="w-full max-w-sm text-center">
      <h1 className="font-display text-3xl font-bold text-ink mb-4">Check your inbox</h1>
      <p className="text-sm text-graphite mb-2">
        We sent a verification link to
      </p>
      {email && (
        <p className="text-sm font-medium text-ink mb-6 break-all">{email}</p>
      )}
      <p className="text-sm text-graphite mb-8">
        Click the link in the email to activate your account.
      </p>
      <VerifyEmailClient email={email} />
    </div>
  );
}
