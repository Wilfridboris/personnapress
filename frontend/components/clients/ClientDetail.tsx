"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { jobsApi } from "@/lib/api";
import type { ClientResponse, Job } from "@/lib/types";

interface Props {
  client: ClientResponse;
}

const secondaryBtn =
  "text-sm border border-[#111111] text-[#111111] px-4 py-2 hover:bg-[#111111] hover:text-white transition-colors rounded-none font-medium";

export function ClientDetail({ client }: Props) {
  const [job, setJob] = useState<Job | null>(null);
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    if (!client.job_id) return;

    setPolling(true);
    let interval: ReturnType<typeof setInterval>;

    async function checkJob() {
      try {
        const j = await jobsApi.get(client.job_id!);
        setJob(j);
        if (j.status === "failed" || j.status === "completed" || j.completed_at) {
          clearInterval(interval);
          setPolling(false);
        }
      } catch {
        clearInterval(interval);
        setPolling(false);
      }
    }

    checkJob();
    interval = setInterval(checkJob, 2000);
    return () => clearInterval(interval);
  }, [client.job_id]);

  const isIngesting =
    polling || (job && (job.status === "pending" || job.status === "in_progress"));

  const hasVoiceProfile = !!client.brand_voice_profile;

  return (
    <section aria-labelledby="bvp-heading">
      <p
        id="bvp-heading"
        className="text-xs font-sans uppercase tracking-widest text-[#111111] mb-4"
      >
        Brand voice
      </p>

      {isIngesting && client.website_url ? (
        <p className="font-mono text-sm text-[#555555]">
          Analyzing {client.website_url}...
        </p>
      ) : !hasVoiceProfile ? (
        <div>
          <p className="text-[#555555] mb-4">
            No voice profile yet. Upload content or complete the voice questionnaire.
          </p>
          <div className="flex gap-3">
            <Link href={`/clients/${client.id}/voice?mode=upload`} className={secondaryBtn}>
              Upload content
            </Link>
            <Link href={`/clients/${client.id}/voice?mode=questionnaire`} className={secondaryBtn}>
              Complete questionnaire
            </Link>
          </div>
        </div>
      ) : (
        <div className="border border-[#E5E5E5] divide-y divide-[#E5E5E5]">
          <div className="p-6">
            <p className="text-xs uppercase tracking-widest text-[#555555] mb-2">
              Profile ready
            </p>
            <p className="text-sm text-[#111111]">Voice profile has been generated.</p>
          </div>
        </div>
      )}
    </section>
  );
}
