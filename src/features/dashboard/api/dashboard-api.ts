import type { DashboardSnapshot, MarketplaceStrategy, StrategyFileView } from "@/features/dashboard/types";

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

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
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

export function getStrategyDownloadUrl(strategyId: string) {
  return `${apiBaseUrl}/api/v1/client/strategies/${strategyId}/download`;
}

export function brokerConnectUrl(provider: "fyers" | "groww") {
  return `${apiBaseUrl}/api/v1/client/brokers/${provider}/connect`;
}
