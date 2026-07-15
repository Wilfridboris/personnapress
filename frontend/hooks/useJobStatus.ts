"use client";

import { useQuery } from "@tanstack/react-query";
import { jobsApi, APIError } from "@/lib/api";
import type { Job } from "@/lib/types";

const TERMINAL_STATUSES = new Set(["complete", "completed", "failed"]);
const POLLING_STATUSES = new Set(["pending", "in_progress"]);

/** Returns true if the job has reached a terminal state (no more polling). */
export function isJobTerminal(job: Job | null | undefined): boolean {
  return !!job && TERMINAL_STATUSES.has(job.status);
}

/**
 * Polls a job by ID every 3 seconds while it is pending or in_progress.
 * Stops polling automatically once the job reaches a terminal state or on auth errors.
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
      const error = query.state.error;
      // Stop polling on auth errors or terminal data
      if (error instanceof APIError && error.status === 401) return false;
      if (!data) return 3000;
      return TERMINAL_STATUSES.has(data.status) ? false : 3000;
    },
    retry: (failureCount, error) => {
      // Never retry on 401 — the session is gone
      if (error instanceof APIError && error.status === 401) return false;
      return failureCount < 2;
    },
    staleTime: 0,
  });

  const job = query.data ?? null;
  // Include the pre-first-fetch window (job=null but jobId is set) so the
  // beforeunload guard is active from the moment generation begins.
  const isPolling = !!jobId && (!job || POLLING_STATUSES.has(job.status));

  return { job, isPolling, error: query.error };
}
