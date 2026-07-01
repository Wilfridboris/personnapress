import { ClientCardSkeleton } from "@/components/clients/ClientCardSkeleton";

export default function ClientsLoading() {
  return (
    <>
      <div className="flex items-center justify-between mb-8">
        <div className="bg-[#E5E5E5] h-9 w-32 animate-pulse rounded-none" />
        <div className="bg-[#E5E5E5] h-10 w-28 animate-pulse rounded-none" />
      </div>
      <div className="space-y-4">
        <ClientCardSkeleton />
        <ClientCardSkeleton />
        <ClientCardSkeleton />
      </div>
    </>
  );
}
