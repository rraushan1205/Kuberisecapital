import type { AdminAnnouncement, AdminExecutionLog, AdminSession, AdminStrategy, AdminUser, ConnectedUser } from "@/features/admin/types";

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export class AdminApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "AdminApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      Accept: "application/json",
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new AdminApiError(payload?.detail || "The admin service could not complete the request.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const adminApi = {
  login: (email: string, password: string) => request<AdminSession>("/api/v1/admin/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/api/v1/admin/auth/logout", { method: "POST" }),
  getSession: () => request<AdminSession>("/api/v1/admin/auth/session"),
  getUsers: () => request<AdminUser[]>("/api/v1/admin/users"),
  getPendingRegistrations: () => request<AdminUser[]>("/api/v1/admin/pending-registrations"),
  approveSubscription: (userId: string) => request<AdminUser>(`/api/v1/admin/subscriptions/${userId}/approve`, { method: "POST" }),
  getConnectedUsers: () => request<ConnectedUser[]>("/api/v1/admin/connected-users"),
  getStrategies: () => request<AdminStrategy[]>("/api/v1/admin/strategies"),
  uploadStrategy: (name: string, script: File) => {
    const body = new FormData();
    body.set("name", name);
    body.set("script", script);
    return request<AdminStrategy>("/api/v1/admin/strategies", { method: "POST", body });
  },
  startStrategy: (strategyId: string) => request<AdminStrategy>(`/api/v1/admin/strategies/${strategyId}/start`, { method: "POST" }),
  stopStrategy: (strategyId: string) => request<AdminStrategy>(`/api/v1/admin/strategies/${strategyId}/stop`, { method: "POST" }),
  forceSquareOff: () => request<void>("/api/v1/admin/force-square-off", { method: "POST" }),
  getLogs: () => request<AdminExecutionLog[]>("/api/v1/admin/logs"),
  getAnnouncements: () => request<AdminAnnouncement[]>("/api/v1/admin/announcements"),
  createAnnouncement: (title: string, message: string) => request<AdminAnnouncement>("/api/v1/admin/announcements", { method: "POST", body: JSON.stringify({ title, message }) }),
};
