"use client";

import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { useAdminUsers } from "@/features/admin/hooks/use-admin-data";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";

export function UsersPage() {
  const { data, isLoading, isError } = useAdminUsers();
  return <div><AdminPageTitle eyebrow="USER MANAGEMENT" title="Registered users">Review account and subscription state for every registered user.</AdminPageTitle><SectionCard><SectionCardHeader eyebrow="ACCOUNT RECORDS" title="Users" />{isLoading ? <AdminLoadingRows /> : isError ? <div className="p-5"><AdminError message="User records could not be loaded." /></div> : !data?.length ? <AdminEmpty message="No user records are available." /> : <div className="overflow-x-auto"><table className="min-w-[760px] w-full text-left"><thead className="border-b border-[var(--line)] bg-[var(--panel-raised)] font-mono text-[10px] uppercase tracking-[0.09em] text-[var(--ink-subtle)]"><tr><th className="px-5 py-3 font-medium">User</th><th className="px-5 py-3 font-medium">Role</th><th className="px-5 py-3 font-medium">Verification</th><th className="px-5 py-3 font-medium">Account</th><th className="px-5 py-3 font-medium">Subscription</th></tr></thead><tbody className="divide-y divide-[var(--line)]">{data.map((user) => <tr key={user.id} className="text-[12px]"><td className="px-5 py-3.5"><p className="font-medium text-[var(--ink)]">{user.full_name || "Name unavailable"}</p><p className="mt-0.5 text-[var(--ink-muted)]">{user.email}</p></td><td className="px-5 py-3.5 text-[var(--ink-muted)]">{user.role}</td><td className="px-5 py-3.5 text-[var(--ink-muted)]">{user.email_verified ? "Verified" : "Not verified"}</td><td className="px-5 py-3.5 text-[var(--ink-muted)]">{user.account_status}</td><td className="px-5 py-3.5 text-[var(--ink-muted)]">{user.subscription_status}</td></tr>)}</tbody></table></div>}</SectionCard></div>;
}
