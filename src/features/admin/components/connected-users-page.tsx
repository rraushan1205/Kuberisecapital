"use client";

import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { useConnectedUsers } from "@/features/admin/hooks/use-admin-data";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";

export function ConnectedUsersPage() {
  const { data, isLoading, isError } = useConnectedUsers();
  return <div><AdminPageTitle eyebrow="CONNECTED USERS" title="Broker connections">This list contains users reported as connected by the broker connection service.</AdminPageTitle><SectionCard><SectionCardHeader eyebrow="ACTIVE CONNECTION RECORDS" title="Connected users" />{isLoading ? <AdminLoadingRows /> : isError ? <div className="p-5"><AdminError message="Connected user records could not be loaded." /></div> : !data?.length ? <AdminEmpty message="No connected users are currently reported." /> : <div className="overflow-x-auto"><table className="min-w-[650px] w-full text-left"><thead className="border-b border-[var(--line)] bg-[var(--panel-raised)] font-mono text-[10px] uppercase tracking-[0.09em] text-[var(--ink-subtle)]"><tr><th className="px-5 py-3 font-medium">User</th><th className="px-5 py-3 font-medium">Provider</th><th className="px-5 py-3 font-medium">Connection</th></tr></thead><tbody className="divide-y divide-[var(--line)]">{data.map((record) => <tr key={`${record.user_id}-${record.provider}`} className="text-[12px]"><td className="px-5 py-3.5"><p className="font-medium text-[var(--ink)]">{record.full_name || "Name unavailable"}</p><p className="mt-0.5 text-[var(--ink-muted)]">{record.email}</p></td><td className="px-5 py-3.5 text-[var(--ink-muted)]">{record.provider}</td><td className="px-5 py-3.5 text-[var(--ink-muted)]">{record.status}</td></tr>)}</tbody></table></div>}</SectionCard></div>;
}
