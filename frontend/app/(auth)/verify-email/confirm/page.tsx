import { Suspense } from "react";
import { VerifyEmailConfirmClient } from "./VerifyEmailConfirmClient";

export default function VerifyEmailConfirmPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-sm text-center">
          <p className="text-sm text-graphite">Verifying your email...</p>
        </div>
      }
    >
      <VerifyEmailConfirmClient />
    </Suspense>
  );
}
