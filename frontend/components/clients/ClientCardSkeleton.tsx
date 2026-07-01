export function ClientCardSkeleton() {
  return (
    <div className="bg-white border border-[#E5E5E5] p-6 rounded-none animate-pulse">
      <div className="bg-[#E5E5E5] h-4 w-3/4 mb-2 rounded-none" />
      <div className="bg-[#E5E5E5] h-3 w-1/2 mb-2 rounded-none" />
      <div className="bg-[#E5E5E5] h-3 w-2/5 mb-2 rounded-none" />
      <div className="bg-[#E5E5E5] h-3 w-1/4 rounded-none" />
    </div>
  );
}
