import type { BrandVoiceProfile, ClientListResponse, ClientResponse, Campaign, DashboardStats, FileListResponse, Job, QuestionnairePayload } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = `${API_URL}/api/v1`;

export class APIError extends Error {
  readonly code: string;
  constructor(message: string, code: string) {
    super(message);
    this.name = "APIError";
    this.code = code;
  }
}

export async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (res.status === 204) {
    return undefined as T;
  }

  let data: Record<string, unknown>;
  try {
    data = (await res.json()) as Record<string, unknown>;
  } catch {
    throw new APIError(`Request failed (${res.status})`, "NETWORK_ERROR");
  }

  if (!res.ok) {
    const errShape = data?.error as { message?: string; code?: string } | undefined;
    const message =
      errShape?.message ??
      (typeof data?.detail === "string" ? data.detail : undefined) ??
      "Something went wrong.";
    const code = errShape?.code ?? "UNKNOWN_ERROR";
    throw new APIError(message, code);
  }

  return data as T;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  return fetchAPI<T>(path, options);
}

export const clientsApi = {
  list: () => apiFetch<ClientListResponse>("/clients"),
  get: (id: string) => apiFetch<ClientResponse>(`/clients/${id}`),
  create: (data: { name: string; website_url?: string }) =>
    apiFetch<ClientResponse>("/clients", { method: "POST", body: JSON.stringify(data) }),
  patch: (
    id: string,
    data: {
      name?: string;
      website_url?: string;
      confirm_url_change?: boolean;
      brand_voice_profile?: BrandVoiceProfile | null;
    },
  ) =>
    apiFetch<ClientResponse | { requires_confirmation: boolean; domain: string }>(
      `/clients/${id}`,
      { method: "PATCH", body: JSON.stringify(data) }
    ),
  delete: (id: string) => apiFetch<void>(`/clients/${id}`, { method: "DELETE" }),
  ingest: (id: string) =>
    apiFetch<{ job_id: string }>(`/clients/${id}/ingest`, { method: "POST" }),
  submitQuestionnaire: (id: string, data: QuestionnairePayload) =>
    apiFetch<{ job_id: string }>(`/clients/${id}/questionnaire`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export const jobsApi = {
  get: (id: string) => apiFetch<Job>(`/jobs/${id}`),
};

export const filesApi = {
  list: (clientId: string) =>
    apiFetch<FileListResponse>(`/clients/${clientId}/files`),
  delete: (clientId: string, filename: string) =>
    apiFetch<void>(`/clients/${clientId}/files/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    }),
};

export const campaignsApi = {
  list: () => apiFetch<Campaign[]>("/campaigns"),
  get: (id: string) => apiFetch<Campaign>(`/campaigns/${id}`),
  create: (data: { client_id: string; brain_dump: string }) =>
    apiFetch<{ job_id: string; campaign_id: string }>("/campaigns", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  approve: (id: string) =>
    apiFetch<Campaign>(`/campaigns/${id}/approve`, { method: "POST" }),
  reject: (id: string) =>
    apiFetch<Campaign>(`/campaigns/${id}/reject`, { method: "POST" }),
  publish: (id: string) =>
    apiFetch<{ ok: boolean; published_urls: Record<string, string> }>(
      `/campaigns/${id}/publish`,
      { method: "POST" }
    ),
};

export const dashboardApi = {
  stats: () => apiFetch<DashboardStats>("/dashboard/stats"),
};
