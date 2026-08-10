import type { DashboardSnapshot, MarketplaceStrategy, StrategyFileView, UserStrategyPermission, StrategyControlResponse } from "@/features/dashboard/types";
import { refreshClientSession } from "@/lib/auth-client";
import { authHeader } from "@/lib/session-storage";

function getApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
  }

  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl) {
    return envUrl.replace(/\/$/, "");
  }

  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  return window.location.origin;
}

const apiBaseUrl = getApiBaseUrl();

class DashboardApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "DashboardApiError";
  }
}

async function getJson<T>(path: string, allowRefresh = true): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
    headers: { Accept: "application/json", ...authHeader() },
  });
  if (response.status === 401 && allowRefresh) {
    try {
      await refreshClientSession();
      return getJson<T>(path, false);
    } catch {
      // Preserve the dashboard error below when a refresh session is unavailable.
    }
  }
  if (!response.ok) throw new DashboardApiError("The dashboard service did not return data.", response.status);
  return response.json() as Promise<T>;
}

export function getDashboardSnapshot() {
  return getJson<DashboardSnapshot>("/api/v1/client/dashboard");
}

export function getMarketplaceStrategies() {
  return getJson<MarketplaceStrategy[]>("/api/v1/client/marketplace/strategies");
}

export function getStrategyFileView(strategyId: string) {
  return getJson<StrategyFileView>(`/api/v1/client/strategies/${strategyId}/view`);
}

/**
 * Downloads a strategy file through the Bearer-authenticated endpoint.
 *
 * A plain `<a download href>` navigation cannot attach the Authorization header,
 * so the file is fetched as a blob and handed to the browser via an object URL.
 */
export async function downloadStrategyFile(strategyId: string, filename: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/client/strategies/${strategyId}/download`, {
    credentials: "include",
    headers: { Accept: "text/x-python", ...authHeader() },
  });
  if (response.status === 401) {
    await refreshClientSession();
    return downloadStrategyFile(strategyId, filename);
  }
  if (!response.ok) throw new DashboardApiError("The strategy file could not be downloaded.", response.status);
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

/**
 * Initiate broker OAuth connection flow.
 * 
 * Makes an authenticated API request to get the broker's OAuth authorization URL,
 * then navigates the browser to that URL. This is necessary because the broker
 * connect endpoint requires authentication to generate the OAuth state parameter.
 */
export async function connectBroker(provider: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/client/brokers/${provider}/connect`, {
    credentials: "include",
    headers: { Accept: "application/json", ...authHeader() },
  });

  if (response.status === 401) {
    try {
      await refreshClientSession();
      return connectBroker(provider);
    } catch {
      throw new DashboardApiError("Authentication required to connect broker.", 401);
    }
  }

  if (!response.ok) {
    throw new DashboardApiError(
      `Failed to initiate broker connection: ${response.status}`,
      response.status
    );
  }

  // Parse JSON response containing the authorize URL
  const data = await response.json();
  const authorizeUrl = data.authorize_url;

  if (!authorizeUrl) {
    throw new DashboardApiError("No authorize URL received from server.", response.status);
  }

  // Navigate to the broker's OAuth page
  window.location.href = authorizeUrl;
}

/**
 * Get user's assigned strategies (admin-managed strategies).
 */
export function getUserStrategyPermissions() {
  return getJson<UserStrategyPermission[]>("/api/v1/client/strategy-permissions");
}

/**
 * Start a strategy execution.
 */
export async function startStrategy(permissionId: number): Promise<StrategyControlResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/client/strategy-permissions/${permissionId}/start`, {
    method: "POST",
    credentials: "include",
    headers: { 
      Accept: "application/json",
      "Content-Type": "application/json",
      ...authHeader() 
    },
  });

  if (response.status === 401) {
    await refreshClientSession();
    return startStrategy(permissionId);
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to start strategy" }));
    throw new DashboardApiError(error.detail || "Failed to start strategy", response.status);
  }

  return response.json() as Promise<StrategyControlResponse>;
}

/**
 * Stop a strategy execution.
 */
export async function stopStrategy(permissionId: number): Promise<StrategyControlResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/client/strategy-permissions/${permissionId}/stop`, {
    method: "POST",
    credentials: "include",
    headers: { 
      Accept: "application/json",
      "Content-Type": "application/json",
      ...authHeader() 
    },
  });

  if (response.status === 401) {
    await refreshClientSession();
    return stopStrategy(permissionId);
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to stop strategy" }));
    throw new DashboardApiError(error.detail || "Failed to stop strategy", response.status);
  }

  return response.json() as Promise<StrategyControlResponse>;
}
