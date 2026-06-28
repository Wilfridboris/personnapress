export function SidebarSkeleton() {
  return (
    <div aria-hidden="true" className="py-2">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="animate-pulse bg-[#E5E5E5] mx-3 h-[44px] mb-0.5"
        />
      ))}
    </div>
  );
}
