"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/features/admin/api/admin-api";

export const adminQueryKeys = {
  session: ["admin", "session"] as const,
  users: ["admin", "users"] as const,
  pending: ["admin", "pending-registrations"] as const,
  connected: ["admin", "connected-users"] as const,
  strategies: ["admin", "strategies"] as const,
  logs: ["admin", "logs"] as const,
  announcements: ["admin", "announcements"] as const,
};

export function useAdminSession() { return useQuery({ queryKey: adminQueryKeys.session, queryFn: adminApi.getSession }); }
export function useAdminUsers() { return useQuery({ queryKey: adminQueryKeys.users, queryFn: adminApi.getUsers }); }
export function usePendingRegistrations() { return useQuery({ queryKey: adminQueryKeys.pending, queryFn: adminApi.getPendingRegistrations }); }
export function useConnectedUsers() { return useQuery({ queryKey: adminQueryKeys.connected, queryFn: adminApi.getConnectedUsers }); }
export function useAdminStrategies() { return useQuery({ queryKey: adminQueryKeys.strategies, queryFn: adminApi.getStrategies }); }
export function useExecutionLogs() { return useQuery({ queryKey: adminQueryKeys.logs, queryFn: adminApi.getLogs }); }
export function useAnnouncements() { return useQuery({ queryKey: adminQueryKeys.announcements, queryFn: adminApi.getAnnouncements }); }

export function useApproveSubscription() {
  const client = useQueryClient();
  return useMutation({ mutationFn: adminApi.approveSubscription, onSuccess: () => Promise.all([client.invalidateQueries({ queryKey: adminQueryKeys.pending }), client.invalidateQueries({ queryKey: adminQueryKeys.users })]) });
}

export function useUploadStrategy() {
  const client = useQueryClient();
  return useMutation({ mutationFn: ({ name, script }: { name: string; script: File }) => adminApi.uploadStrategy(name, script), onSuccess: () => client.invalidateQueries({ queryKey: adminQueryKeys.strategies }) });
}

export function useStrategyCommand() {
  const client = useQueryClient();
  return useMutation({ mutationFn: ({ strategyId, command }: { strategyId: string; command: "start" | "stop" }) => command === "start" ? adminApi.startStrategy(strategyId) : adminApi.stopStrategy(strategyId), onSuccess: () => Promise.all([client.invalidateQueries({ queryKey: adminQueryKeys.strategies }), client.invalidateQueries({ queryKey: adminQueryKeys.logs })]) });
}

export function useForceSquareOff() {
  const client = useQueryClient();
  return useMutation({ mutationFn: adminApi.forceSquareOff, onSuccess: () => client.invalidateQueries({ queryKey: adminQueryKeys.logs }) });
}

export function useCreateAnnouncement() {
  const client = useQueryClient();
  return useMutation({ mutationFn: ({ title, message }: { title: string; message: string }) => adminApi.createAnnouncement(title, message), onSuccess: () => client.invalidateQueries({ queryKey: adminQueryKeys.announcements }) });
}
