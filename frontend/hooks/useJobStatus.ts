"use client";

import { useQuery } from "@tanstack/react-query";
import { jobsApi } from "@/lib/api";
import type { Job } from "@/lib/types";

const TERMINAL_STATUSES = new Set(["complete", "completed", "failed"]);
const POLLING_STATUSES = new Set(["pending", "in_progress"]);

/** Returns true if the job has reached a terminal state (no more polling). */
export function isJobTerminal(job: Job | null | undefined): boolean {
  return !!job && TERMINAL_STATUSES.has(job.status);
}

/**
 * Polls a job by ID every 2 seconds while it is pending or in_progress.
 * Stops polling automatically once the job reaches a terminal state.
 */
export function useJobStatus(jobId: string | null | undefined) {
  const query = useQuery<Job | null>({
    queryKey: ["job", jobId],
    queryFn: async () => {
      if (!jobId) return null;
      return jobsApi.get(jobId);
    },
    enabled: !!jobId && jobId.length > 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      return TERMINAL_STATUSES.has(data.status) ? false : 3000;
    },
    staleTime: 0,
  });

  const job = query.data ?? null;
  // Include the pre-first-fetch window (job=null but jobId is set) so the
  // beforeunload guard is active from the moment generation begins.
  const isPolling = !!jobId && (!job || POLLING_STATUSES.has(job.status));

  return { job, isPolling, error: query.error };
}
