import type { Client, Campaign, DashboardStats } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = `${API_URL}/api/v1`;

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: "Request failed" } }));
    throw new Error(error.error?.message || error.detail || "Request failed");
  }
  return res.json() as Promise<T>;
}

export const clientsApi = {
  list: () => apiFetch<Client[]>("/clients"),
  get: (id: string) => apiFetch<Client>(`/clients/${id}`),
  create: (data: { name: string; website_url?: string }) =>
    apiFetch<Client>("/clients", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Client>) =>
    apiFetch<Client>(`/clients/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/clients/${id}`, { method: "DELETE" }),
  ingest: (id: string) =>
    apiFetch<{ job_id: string }>(`/clients/${id}/ingest`, { method: "POST" }),
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
