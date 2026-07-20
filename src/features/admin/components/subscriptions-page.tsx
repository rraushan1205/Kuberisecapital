"use client";

import { Check, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { useApproveSubscription, usePendingRegistrations } from "@/features/admin/hooks/use-admin-data";

export function SubscriptionsPage() {
  const { data, isLoading, isError } = usePendingRegistrations();
  const approval = useApproveSubscription();
  return <div><AdminPageTitle eyebrow="SUBSCRIPTION APPROVAL" title="Approve eligible accounts">Approval activates a verified user account and its subscription. Unverified accounts cannot be approved.</AdminPageTitle>{approval.error && <div className="mb-4"><AdminError message="The subscription could not be approved. Confirm the user’s email verification and try again." /></div>}<SectionCard><SectionCardHeader eyebrow="ELIGIBLE ACCOUNTS" title="Subscription review" />{isLoading ? <AdminLoadingRows /> : isError ? <div className="p-5"><AdminError message="Subscription candidates could not be loaded." /></div> : !data?.length ? <AdminEmpty message="No subscriptions are awaiting approval." /> : <div className="divide-y divide-[var(--line)]">{data.map((user) => <div key={user.id} className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"><div><p className="text-[13px] font-medium text-[var(--ink)]">{user.full_name || "Name unavailable"}</p><p className="mt-0.5 text-[12px] text-[var(--ink-muted)]">{user.email}</p></div>{user.email_verified ? <Button variant="primary" size="sm" onClick={() => approval.mutate(user.id)} disabled={approval.isPending}><>{approval.isPending ? <LoaderCircle size={14} className="animate-spin" /> : <Check size={14} />} Approve subscription</></Button> : <span className="text-[12px] text-[var(--ink-subtle)]">Email verification required</span>}</div>)}</div>}</SectionCard></div>;
}
