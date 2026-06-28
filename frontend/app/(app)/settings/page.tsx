import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Settings",
  robots: { index: false },
};

export default function SettingsPage() {
  return (
    <>
      <header className="mb-10">
        <h1 className="font-display text-3xl font-bold text-ink mb-1">
          Settings
        </h1>
        <p className="text-sm text-graphite font-mono">
          Configure your API keys and publishing credentials.
        </p>
      </header>

      <div className="border border-border p-8 text-center text-graphite font-mono text-sm">
        Settings panel coming in the next release.
        <br />
        <span className="text-xs mt-2 block">
          For now, configure credentials directly in the database or via the backend .env file.
        </span>
      </div>
    </>
  );
}
