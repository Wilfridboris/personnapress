"use client";

import { useQuery } from "@tanstack/react-query";
import { jobsApi } from "@/lib/api";
import type { Job } from "@/lib/types";

const TERMINAL_STATUSES = new Set(["completed", "failed", "complete"]);

/** Returns true if the job has reached a terminal state (no more polling). */
export function isJobTerminal(job: Job | null | undefined): boolean {
  return !!job && TERMINAL_STATUSES.has(job.status);
}

/**
 * Polls a job by ID every 2 seconds while it is pending or in_progress.
 * Stops polling automatically once the job reaches a terminal state.
 *
 * @param jobId - The job UUID string, or null/undefined to skip polling.
 */
export function useJobStatus(jobId: string | null | undefined) {
  return useQuery<Job | null>({
    queryKey: ["job", jobId],
    queryFn: async () => {
      if (!jobId) return null;
      return jobsApi.get(jobId);
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      return TERMINAL_STATUSES.has(data.status) ? false : 2000;
    },
    staleTime: 0,
  });
}
