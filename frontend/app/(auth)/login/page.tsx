import type { Metadata } from "next";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = {
  title: "Log in | PersonnaPress",
};

export default function LoginPage() {
  return (
    <div className="w-full max-w-sm">
      <h1 className="font-display text-3xl font-bold text-ink mb-8 text-center">
        PersonnaPress
      </h1>
      <LoginForm />
    </div>
  );
}
