export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="px-4 py-8">
      {children}
    </main>
  );
}
