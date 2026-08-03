import type { AdminAnnouncement, AdminExecutionLog, AdminSession, AdminStrategy, AdminSubscriptionPlan, AdminUser, AdminUserDetail, BrokerAccountsResponse, SubscriptionPlanInput, UpdateUserSubscriptionInput } from "@/features/admin/types";
import { authHeader, clearSession, getRefreshToken, setSession } from "@/lib/session-storage";

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

type AdminAuthPayload = AdminSession & { access_token: string; refresh_token: string };

export class AdminApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "AdminApiError";
  }
}

let refreshInFlight: Promise<AdminSession> | null = null;

async function parseError(response: Response) {
  const payload = await response.json().catch(() => null) as { detail?: string } | null;
  return new AdminApiError(payload?.detail || "The admin service could not complete the request.", response.status);
}

async function refreshAdminSession(): Promise<AdminSession> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refreshToken = getRefreshToken("admin");
      if (!refreshToken) throw new AdminApiError("No admin session to refresh.", 401);
      const response = await fetch(`${apiBaseUrl}/api/v1/admin/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) throw await parseError(response);
      const payload = await response.json() as AdminAuthPayload;
      setSession({ access_token: payload.access_token, refresh_token: payload.refresh_token }, "admin");
      return payload;
    })().finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

async function request<T>(path: string, init?: RequestInit, allowRefresh = true): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      Accept: "application/json",
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...authHeader("admin"),
      ...init?.headers,
    },
  });
  if (response.status === 401 && allowRefresh && !path.startsWith("/api/v1/admin/auth/")) {
    try {
      await refreshAdminSession();
      return request<T>(path, init, false);
    } catch {
      // Preserve the original endpoint error so callers can present its context.
    }
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const adminApi = {
  login: async (email: string, password: string) => {
    const payload = await request<AdminAuthPayload>("/api/v1/admin/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false);
    setSession({ access_token: payload.access_token, refresh_token: payload.refresh_token }, "admin");
    return payload;
  },
  refresh: () => refreshAdminSession(),
  logout: async () => {
    try {
      await request<void>("/api/v1/admin/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: getRefreshToken("admin") }) }, false);
    } finally {
      clearSession("admin");
    }
  },
  getSession: () => request<AdminSession>("/api/v1/admin/auth/session"),
  getUsers: () => request<AdminUser[]>("/api/v1/admin/users"),
  getPendingRegistrations: () => request<AdminUser[]>("/api/v1/admin/pending-registrations"),
  approveUser: (userId: string) => request<AdminUser>(`/api/v1/admin/users/${userId}/approve`, { method: "POST" }),
  rejectUser: (userId: string) => request<AdminUser>(`/api/v1/admin/users/${userId}/reject`, { method: "POST" }),
  approveSubscription: (userId: string) => request<AdminUser>(`/api/v1/admin/subscriptions/${userId}/approve`, { method: "POST" }),
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
  getSubscriptionPlans: () => request<AdminSubscriptionPlan[]>("/api/v1/admin/subscription-plans"),
  createSubscriptionPlan: (plan: SubscriptionPlanInput) => request<AdminSubscriptionPlan>("/api/v1/admin/subscription-plans", { method: "POST", body: JSON.stringify(plan) }),
  updateSubscriptionPlan: (planId: string, plan: SubscriptionPlanInput) => request<AdminSubscriptionPlan>(`/api/v1/admin/subscription-plans/${planId}`, { method: "PUT", body: JSON.stringify(plan) }),
  deleteSubscriptionPlan: (planId: string) => request<void>(`/api/v1/admin/subscription-plans/${planId}`, { method: "DELETE" }),
  getUserDetail: (userId: string) => request<AdminUserDetail>(`/api/v1/admin/users/${userId}`),
  updateUserSubscription: (userId: string, input: UpdateUserSubscriptionInput) => request<AdminUserDetail>(`/api/v1/admin/users/${userId}/subscription`, { method: "PUT", body: JSON.stringify(input) }),
  getBrokerAccounts: (skip = 0, limit = 20, provider?: string, status?: string, userId?: string) => {
    const params = new URLSearchParams();
    params.set("skip", skip.toString());
    params.set("limit", limit.toString());
    if (provider) params.set("provider", provider);
    if (status) params.set("status", status);
    if (userId) params.set("user_id", userId);
    return request<BrokerAccountsResponse>(`/api/v1/admin/brokers/accounts?${params.toString()}`);
  },
};
