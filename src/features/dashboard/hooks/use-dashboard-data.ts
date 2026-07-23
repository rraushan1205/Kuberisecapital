"use client";

import { useQuery } from "@tanstack/react-query";
import { getDashboardSnapshot, getMarketplaceStrategies } from "@/features/dashboard/api/dashboard-api";
import { 
  USE_MOCK_DATA, 
  MOCK_DASHBOARD_SNAPSHOT, 
  MOCK_MARKETPLACE_STRATEGIES,
  MOCK_OPEN_POSITIONS,
  MOCK_CLOSED_POSITIONS,
  MOCK_EXECUTION_LOGS,
  MOCK_PNL_DAILY_CHART,
  MOCK_PNL_OVERALL_CHART,
} from "@/features/dashboard/lib/mock-data";

// Simulate API delay for realistic loading states
const simulateApiDelay = <T,>(data: T): Promise<T> => {
  return new Promise((resolve) => setTimeout(() => resolve(data), 400));
};

export function useDashboardSnapshot() {
  return useQuery({ 
    queryKey: ["dashboard", "snapshot"], 
    queryFn: USE_MOCK_DATA 
      ? () => simulateApiDelay(MOCK_DASHBOARD_SNAPSHOT)
      : getDashboardSnapshot 
  });
}

export function useMarketplaceStrategies() {
  return useQuery({ 
    queryKey: ["dashboard", "marketplace", "strategies"], 
    queryFn: USE_MOCK_DATA 
      ? () => simulateApiDelay(MOCK_MARKETPLACE_STRATEGIES)
      : getMarketplaceStrategies 
  });
}

export function usePositions() {
  return useQuery({
    queryKey: ["dashboard", "positions"],
    queryFn: USE_MOCK_DATA
      ? () => simulateApiDelay({ open: MOCK_OPEN_POSITIONS, closed: MOCK_CLOSED_POSITIONS })
      : async () => {
          // TODO: Replace with actual API call
          // return fetch('/api/v1/client/positions').then(r => r.json())
          throw new Error("API not implemented");
        }
  });
}

export function useExecutionLogs() {
  return useQuery({
    queryKey: ["dashboard", "executions"],
    queryFn: USE_MOCK_DATA
      ? () => simulateApiDelay(MOCK_EXECUTION_LOGS)
      : async () => {
          // TODO: Replace with actual API call
          // return fetch('/api/v1/client/executions').then(r => r.json())
          throw new Error("API not implemented");
        }
  });
}

export function usePnlChartData() {
  return useQuery({
    queryKey: ["dashboard", "pnl", "history"],
    queryFn: USE_MOCK_DATA
      ? () => simulateApiDelay({ daily: MOCK_PNL_DAILY_CHART, overall: MOCK_PNL_OVERALL_CHART })
      : async () => {
          // TODO: Replace with actual API call
          // return fetch('/api/v1/client/pnl/history').then(r => r.json())
          throw new Error("API not implemented");
        }
  });
}
