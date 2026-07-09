import type { BrandVoiceProfile, CampaignCreate, CampaignListResponse, ClientListResponse, ClientResponse, Campaign, ConnectionCreatePayload, DashboardStats, FileListResponse, Job, PlatformConnectionStatus, QuestionnairePayload, SubscriptionInfo } from "./types";

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
  listPaginated: (params: {
    client_id?: string;
    status?: string;
    page?: number;
    per_page?: number;
  }) => {
    const query = new URLSearchParams();
    if (params.client_id) query.set("client_id", params.client_id);
    if (params.status) query.set("status", params.status);
    if (params.page != null) query.set("page", String(params.page));
    if (params.per_page != null) query.set("per_page", String(params.per_page));
    const qs = query.toString();
    return apiFetch<CampaignListResponse>(`/campaigns${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => apiFetch<Campaign>(`/campaigns/${id}`),
  create: (data: CampaignCreate) =>
    apiFetch<{ job_id: string; campaign_id: string }>("/campaigns", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  approve: (id: string) =>
    apiFetch<{ id: string; status: string; client_id: string }>(`/campaigns/${id}/approve`, { method: "POST" }),
  reject: (id: string, reason?: string) =>
    apiFetch<{ id: string; status: string; rejection_reason: string | null }>(`/campaigns/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? null }),
    }),
  regenerate: (id: string) =>
    apiFetch<{ campaign_id: string; job_id: string }>(`/campaigns/${id}/regenerate`, { method: "POST" }),
  publishNow: (id: string) =>
    apiFetch<{ job_id: string }>(`/campaigns/${id}/publish`, { method: "POST" }),
  regenerateImage: (id: string) =>
    apiFetch<{ image_url: string; image_regen_count: number }>(
      `/campaigns/${id}/image/regenerate`,
      { method: "POST" }
    ),
  patch: (id: string, data: { blog_html?: string; x_post?: string; linkedin_post?: string }) =>
    apiFetch<Campaign>(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  schedule: (id: string, scheduledAt: string) =>
    apiFetch<{ job_id: string; scheduled_at: string }>(`/campaigns/${id}/publish/schedule`, {
      method: "POST",
      body: JSON.stringify({ scheduled_at: scheduledAt }),
    }),
  cancelSchedule: (id: string) =>
    apiFetch<{ campaign_id: string; status: string }>(`/campaigns/${id}/publish/schedule`, {
      method: "DELETE",
    }),
  retryPublish: (id: string, platform: string) =>
    apiFetch<{ job_id: string }>(`/campaigns/${id}/publish/retry`, {
      method: "POST",
      body: JSON.stringify({ platform }),
    }),
};

export const dashboardApi = {
  stats: () => apiFetch<DashboardStats>("/dashboard/stats"),
};

export const authApi = {
  completeOnboarding: () =>
    apiFetch<{ status: string }>("/auth/complete-onboarding", { method: "POST" }),
};

export const subscriptionsApi = {
  getMe: () => apiFetch<SubscriptionInfo>("/subscriptions/me"),
  getStatus: () => apiFetch<{ status: string }>("/subscriptions/status"),
  createPortal: () => apiFetch<{ portal_url: string }>("/subscriptions/portal", { method: "POST" }),
};

export const publishingApi = {
  listConnections: (clientId: string) =>
    apiFetch<{ items: PlatformConnectionStatus[] }>(`/clients/${clientId}/connections`),
  createConnection: (clientId: string, data: ConnectionCreatePayload) =>
    apiFetch<PlatformConnectionStatus>(`/clients/${clientId}/connections`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteConnection: (clientId: string, platform: string) =>
    apiFetch<void>(`/clients/${clientId}/connections/${platform}`, { method: "DELETE" }),
  getWebflowCollections: (clientId: string, token: string) =>
    apiFetch<{ collections: { id: string; name: string }[] }>(
      `/clients/${clientId}/webflow/collections?token=${encodeURIComponent(token)}`
    ),
  listGitHubRepos: (clientId: string) =>
    apiFetch<{ repos: { full_name: string; private: boolean }[] }>(
      `/clients/${clientId}/connections/github/repos`
    ),
  selectGitHubRepo: (clientId: string, repoFullName: string) =>
    apiFetch<{ platform: string; connected: boolean; account_identifier: string }>(
      `/clients/${clientId}/connections/github/repo`,
      { method: "PATCH", body: JSON.stringify({ repo_full_name: repoFullName }) }
    ),
};
