"use client";

import { AlertTriangle, FileCode2, Loader2, Play, Square } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUserStrategyPermissions, startStrategy, stopStrategy } from "@/features/dashboard/api/dashboard-api";
import { DataError, DataUnavailable } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";
import { Button } from "@/components/ui/button";
import { useState } from "react";

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function MyStrategiesPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["userStrategyPermissions"],
    queryFn: getUserStrategyPermissions,
    refetchInterval: 10000, // Refetch every 10 seconds to get live status
  });

  const [actionInProgress, setActionInProgress] = useState<number | null>(null);

  const startMutation = useMutation({
    mutationFn: (permissionId: number) => startStrategy(permissionId),
    onMutate: (permissionId) => {
      setActionInProgress(permissionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userStrategyPermissions"] });
    },
    onError: (error: Error) => {
      alert(`Failed to start strategy: ${error.message}`);
    },
    onSettled: () => {
      setActionInProgress(null);
    },
  });

  const stopMutation = useMutation({
    mutationFn: (permissionId: number) => stopStrategy(permissionId),
    onMutate: (permissionId) => {
      setActionInProgress(permissionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userStrategyPermissions"] });
    },
    onError: (error: Error) => {
      alert(`Failed to stop strategy: ${error.message}`);
    },
    onSettled: () => {
      setActionInProgress(null);
    },
  });

  return (
    <div>
      <WorkspacePageTitle eyebrow="MY STRATEGIES" title="Assigned strategies">
        Strategies assigned to you by an administrator. Start or stop execution as needed.
      </WorkspacePageTitle>

      {isLoading ? (
        <div aria-label="Loading strategies" aria-busy="true" className="grid gap-4 md:grid-cols-2">
          <div className="h-48 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" />
          <div className="h-48 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" />
        </div>
      ) : (
        <SectionCard>
          <SectionCardHeader eyebrow="ADMIN-ASSIGNED" title="Available strategies" />
          {isError ? (
            <div className="p-5">
              <DataError message="Failed to load strategies. Please try again later." />
            </div>
          ) : !data?.length ? (
            <DataUnavailable message="No strategies have been assigned to you yet. Contact your administrator." />
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {data.map((permission) => (
                <article key={permission.id} className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2.5 mb-3">
                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
                          <FileCode2 size={17} />
                        </span>
                        <div className="min-w-0 flex-1">
                          <h2 className="text-[15px] font-semibold text-[var(--ink)]">
                            {permission.strategy_name}
                          </h2>
                          <p className="mt-0.5 text-[11px] text-[var(--ink-muted)]">
                            Assigned {formatDate(permission.assigned_at)}
                          </p>
                        </div>
                      </div>

                      <p className="text-[12px] leading-5 text-[var(--ink-subtle)] mb-3">
                        {permission.strategy_description}
                      </p>

                      {/* Status badges */}
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        {permission.is_running ? (
                          <span className="rounded-md border border-[var(--positive)] bg-[var(--positive-soft)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--positive)]">
                            RUNNING
                          </span>
                        ) : (
                          <span className="rounded-md border border-[var(--line)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--ink-muted)]">
                            STOPPED
                          </span>
                        )}

                        {!permission.is_active && (
                          <span className="rounded-md border border-[var(--warning)] bg-[var(--warning-soft)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--warning)]">
                            DEACTIVATED
                          </span>
                        )}

                        {permission.has_open_position && (
                          <span className="rounded-md border border-[var(--accent)] bg-[var(--accent-soft)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--accent)]">
                            POSITION OPEN
                          </span>
                        )}
                      </div>

                      {/* Position details */}
                      {permission.position_details && (
                        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] px-3 py-2 text-[11px] text-[var(--ink-muted)] mb-3">
                          <p>
                            <strong className="text-[var(--ink)]">Position:</strong>{" "}
                            {permission.position_details.symbol} × {permission.position_details.qty}
                            {permission.position_details.entry_price && (
                              <> @ ₹{permission.position_details.entry_price.toFixed(2)}</>
                            )}
                          </p>
                          {permission.position_details.current_pnl !== undefined && (
                            <p className="mt-1">
                              <strong className="text-[var(--ink)]">Current P&L:</strong>{" "}
                              <span
                                className={
                                  permission.position_details.current_pnl >= 0
                                    ? "text-[var(--positive)]"
                                    : "text-[var(--danger)]"
                                }
                              >
                                ₹{permission.position_details.current_pnl.toFixed(2)}
                              </span>
                            </p>
                          )}
                        </div>
                      )}

                      {/* Error message */}
                      {permission.error_message && (
                        <div className="flex items-start gap-2 rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2 mb-3">
                          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-[var(--danger)]" />
                          <p className="text-[11px] text-[var(--danger)]">{permission.error_message}</p>
                        </div>
                      )}

                      {/* Config details */}
                      {Object.keys(permission.config).length > 0 && (
                        <details className="text-[11px] text-[var(--ink-muted)]">
                          <summary className="cursor-pointer hover:text-[var(--ink)]">
                            Configuration parameters
                          </summary>
                          <pre className="mt-2 rounded bg-[var(--panel-raised)] p-2 font-mono text-[10px] overflow-x-auto">
                            {JSON.stringify(permission.config, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>

                    {/* Control buttons */}
                    <div className="flex shrink-0 gap-2">
                      {permission.is_running ? (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => stopMutation.mutate(permission.id)}
                          disabled={
                            !permission.is_active ||
                            actionInProgress === permission.id ||
                            stopMutation.isPending
                          }
                        >
                          {actionInProgress === permission.id ? (
                            <>
                              <Loader2 size={14} className="animate-spin" />
                              Stopping...
                            </>
                          ) : (
                            <>
                              <Square size={14} />
                              Stop
                            </>
                          )}
                        </Button>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => startMutation.mutate(permission.id)}
                          disabled={
                            !permission.is_active ||
                            actionInProgress === permission.id ||
                            startMutation.isPending
                          }
                        >
                          {actionInProgress === permission.id ? (
                            <>
                              <Loader2 size={14} className="animate-spin" />
                              Starting...
                            </>
                          ) : (
                            <>
                              <Play size={14} />
                              Start
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionCard>
      )}
    </div>
  );
}
