"use client";

import { FileCode2, LockKeyhole } from "lucide-react";
import { DataError, DataUnavailable } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { useMarketplaceStrategies } from "@/features/dashboard/hooks/use-dashboard-data";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";

export function MarketplacePage() {
  const { data, isLoading, isError } = useMarketplaceStrategies();
  return (
    <div>
      <WorkspacePageTitle eyebrow="MARKETPLACE" title="Published strategies">Strategies become visible here only after an administrator publishes them to your account. Strategy settings and Python files are read-only.</WorkspacePageTitle>
      {isLoading ? <div aria-label="Loading strategies" aria-busy="true" className="grid gap-4 md:grid-cols-2"><div className="h-44 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" /><div className="h-44 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" /></div> : (
        <SectionCard>
          <SectionCardHeader eyebrow="ADMIN-PUBLISHED" title="Available strategies" />
          {isError ? <div className="p-5"><DataError message="Strategy availability could not be loaded. Please try again when the account service is available." /></div> : data?.length ? <div className="grid divide-y divide-[var(--line)] md:grid-cols-2 md:divide-x md:divide-y-0">{data.map((strategy) => <article key={strategy.id} className="p-5"><div className="mb-7 flex items-center justify-between gap-4"><span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]"><FileCode2 size={17} /></span>{strategy.status && <span className="rounded-md border border-[var(--line)] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.08em] text-[var(--ink-muted)]">{strategy.status}</span>}</div><h2 className="text-[15px] font-semibold text-[var(--ink)]">{strategy.name}</h2><p className="mt-2 truncate font-mono text-[11px] text-[var(--ink-muted)]">{strategy.scriptFileName || "Script details are restricted"}</p><p className="mt-4 text-[12px] leading-5 text-[var(--ink-muted)]">This strategy is made available and updated exclusively by an administrator.</p></article>)}</div> : <DataUnavailable message="No strategies have been published to this account." />}
        </SectionCard>
      )}
      <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] px-4 py-3.5 text-[12px] leading-5 text-[var(--ink-muted)]"><LockKeyhole size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" /> <span>Python implementation files are stored in the administrator workspace. This portal can only display the published strategy record.</span></div>
    </div>
  );
}
