import type { DashboardSnapshot, MarketplaceStrategy } from "@/features/dashboard/types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

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

export function brokerConnectUrl(provider: "fyers" | "groww") {
  return `${apiBaseUrl}/api/v1/client/brokers/${provider}/connect`;
}
