import type { DashboardSnapshot, MarketplaceStrategy, StrategyFileView } from "@/features/dashboard/types";
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
 * Generate broker connection URL for OAuth flow
 */
export function brokerConnectUrl(provider: string): string {
  return `${apiBaseUrl}/api/v1/client/brokers/${provider}/connect`;
}
