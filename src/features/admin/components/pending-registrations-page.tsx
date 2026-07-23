"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { usePendingRegistrations } from "@/features/admin/hooks/use-admin-data";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { Button } from "@/components/ui/button";
import { adminApi } from "@/features/admin/api/admin-api";
import { formatDateTime } from "@/features/admin/lib/format";

export function PendingRegistrationsPage() {
  const { data, isLoading, isError, refetch } = usePendingRegistrations();
  const [processingId, setProcessingId] = useState<string | null>(null);

  const approveMutation = useMutation({
    mutationFn: (userId: string) => adminApi.approveUser(userId),
    onSuccess: () => {
      refetch();
      setProcessingId(null);
    },
    onError: () => {
      setProcessingId(null);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (userId: string) => adminApi.rejectUser(userId),
    onSuccess: () => {
      refetch();
      setProcessingId(null);
    },
    onError: () => {
      setProcessingId(null);
    },
  });

  const handleApprove = (userId: string) => {
    setProcessingId(userId);
    approveMutation.mutate(userId);
  };

  const handleReject = (userId: string) => {
    setProcessingId(userId);
    rejectMutation.mutate(userId);
  };

  return (
    <div>
      <AdminPageTitle eyebrow="PENDING REGISTRATIONS" title="Registration review">
        Review and approve new user registrations.
      </AdminPageTitle>
      <SectionCard>
        <SectionCardHeader eyebrow="AWAITING REVIEW" title="Pending accounts" />
        {isLoading ? (
          <AdminLoadingRows />
        ) : isError ? (
          <div className="p-5">
            <AdminError message="Pending registrations could not be loaded." />
          </div>
        ) : !data?.length ? (
          <AdminEmpty message="No registrations are awaiting review." />
        ) : (
          <div className="divide-y divide-[var(--line)]">
            {data.map((user) => (
              <div key={user.id} className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
                <div className="flex-1 min-w-[200px]">
                  <p className="text-[13px] font-medium text-[var(--ink)]">
                    {user.full_name || "Name not provided"}
                  </p>
                  <p className="mt-0.5 text-[12px] text-[var(--ink-muted)]">{user.email}</p>
                  <p className="mt-1 text-[11px] text-[var(--ink-muted)]">
                    Registered: {formatDateTime(user.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded-md border border-[var(--line)] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.08em] text-[var(--ink-muted)]">
                    {user.email_verified ? "Email verified" : "Email unverified"}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleApprove(user.id)}
                      disabled={processingId === user.id}
                      className="bg-green-50 hover:bg-green-100 border-green-200 text-green-700 hover:text-green-800"
                    >
                      {processingId === user.id && approveMutation.isPending ? "Approving..." : "Approve"}
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleReject(user.id)}
                      disabled={processingId === user.id}
                    >
                      {processingId === user.id && rejectMutation.isPending ? "Rejecting..." : "Reject"}
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
