export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F9F9F6] flex items-start justify-center pt-16 px-4">
      {children}
    </div>
  );
}
