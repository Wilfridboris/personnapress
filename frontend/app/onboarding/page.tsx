import type { Metadata } from "next";
import { headers } from "next/headers";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";

export const metadata: Metadata = {
  title: "Welcome | PersonnaPress",
  robots: { index: false },
};

export default async function OnboardingPage() {
  // Server component reads the onboarding_step from the request header forwarded
  // by proxy.ts (decoded from the JWT). The client component initializes step state
  // from this value so returning users resume where they left off (AC 1).
  const headerStore = await headers();
  const rawStep = headerStore.get("x-onboarding-step");
  const parsed = rawStep != null ? parseInt(rawStep, 10) : NaN;
  const initialStep = Number.isFinite(parsed) ? parsed : null;

  return <OnboardingFlow initialStep={initialStep} />;
}
