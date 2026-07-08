import type { Metadata } from "next";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";

export const metadata: Metadata = {
  title: "Welcome | PersonnaPress",
  robots: { index: false },
};

export default function OnboardingPage() {
  return <OnboardingFlow />;
}
