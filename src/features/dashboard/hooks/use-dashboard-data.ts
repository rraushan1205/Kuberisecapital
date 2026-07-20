"use client";

import { useQuery } from "@tanstack/react-query";
import { getDashboardSnapshot, getMarketplaceStrategies } from "@/features/dashboard/api/dashboard-api";

export function useDashboardSnapshot() {
  return useQuery({ queryKey: ["dashboard", "snapshot"], queryFn: getDashboardSnapshot });
}

export function useMarketplaceStrategies() {
  return useQuery({ queryKey: ["dashboard", "marketplace", "strategies"], queryFn: getMarketplaceStrategies });
}
