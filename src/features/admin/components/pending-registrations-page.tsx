"use client";

import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { usePendingRegistrations } from "@/features/admin/hooks/use-admin-data";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";

export function PendingRegistrationsPage() {
  const { data, isLoading, isError } = usePendingRegistrations();
  return <div><AdminPageTitle eyebrow="PENDING REGISTRATIONS" title="Registration review">Only verified accounts can proceed to subscription approval.</AdminPageTitle><SectionCard><SectionCardHeader eyebrow="AWAITING REVIEW" title="Pending accounts" />{isLoading ? <AdminLoadingRows /> : isError ? <div className="p-5"><AdminError message="Pending registrations could not be loaded." /></div> : !data?.length ? <AdminEmpty message="No registrations are awaiting review." /> : <div className="divide-y divide-[var(--line)]">{data.map((user) => <div key={user.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"><div><p className="text-[13px] font-medium text-[var(--ink)]">{user.full_name || "Name unavailable"}</p><p className="mt-0.5 text-[12px] text-[var(--ink-muted)]">{user.email}</p></div><span className="rounded-md border border-[var(--line)] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.08em] text-[var(--ink-muted)]">{user.email_verified ? "Email verified" : "Email unverified"}</span></div>)}</div>}</SectionCard></div>;
}
