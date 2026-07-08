import type { Metadata } from "next";
import { RegisterForm } from "./RegisterForm";

export const metadata: Metadata = {
  title: "Create account | PersonnaPress",
};

export default function RegisterPage() {
  return (
    <div className="w-full max-w-sm">
      <h1 className="font-display text-3xl font-bold text-ink mb-8 text-center">
        PersonnaPress
      </h1>
      <RegisterForm />
    </div>
  );
}
