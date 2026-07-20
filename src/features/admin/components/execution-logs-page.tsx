"use client";

import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { useExecutionLogs } from "@/features/admin/hooks/use-admin-data";
import { formatDateTime, humanizeIdentifier } from "@/features/admin/lib/format";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";

export function ExecutionLogsPage() {
  const { data, isLoading, isError } = useExecutionLogs();
  return <div><AdminPageTitle eyebrow="EXECUTION LOGS" title="Engine command record">A record is created after the configured trading engine accepts an administrative command.</AdminPageTitle><SectionCard><SectionCardHeader eyebrow="MOST RECENT FIRST" title="Execution activity" />{isLoading ? <AdminLoadingRows rows={6} /> : isError ? <div className="p-5"><AdminError message="Execution logs could not be loaded." /></div> : !data?.length ? <AdminEmpty message="No execution commands have been recorded." /> : <div className="overflow-x-auto"><table className="min-w-[760px] w-full text-left"><thead className="border-b border-[var(--line)] bg-[var(--panel-raised)] font-mono text-[10px] uppercase tracking-[0.09em] text-[var(--ink-subtle)]"><tr><th className="px-5 py-3 font-medium">Time</th><th className="px-5 py-3 font-medium">Command</th><th className="px-5 py-3 font-medium">Detail</th><th className="px-5 py-3 font-medium">Strategy</th></tr></thead><tbody className="divide-y divide-[var(--line)]">{data.map((log) => <tr key={log.id} className="text-[12px]"><td className="whitespace-nowrap px-5 py-3.5 text-[var(--ink-muted)]">{formatDateTime(log.created_at)}</td><td className="whitespace-nowrap px-5 py-3.5 font-medium text-[var(--ink)]">{humanizeIdentifier(log.action)}</td><td className="max-w-[440px] px-5 py-3.5 text-[var(--ink-muted)]">{log.message}</td><td className="px-5 py-3.5 font-mono text-[10px] text-[var(--ink-subtle)]">{log.strategy_id || "All positions"}</td></tr>)}</tbody></table></div>}</SectionCard></div>;
}
