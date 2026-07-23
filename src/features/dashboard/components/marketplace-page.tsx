"use client";

import { Download, Eye, FileCode2, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { DataError, DataUnavailable } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { useMarketplaceStrategies } from "@/features/dashboard/hooks/use-dashboard-data";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

export function MarketplacePage() {
  const { data, isLoading, isError } = useMarketplaceStrategies();
  
  return (
    <div>
      <WorkspacePageTitle eyebrow="MARKETPLACE" title="Published strategies">
        Strategies become visible here after an administrator uploads them. You can view and download Python files but cannot edit them.
      </WorkspacePageTitle>
      
      {isLoading ? (
        <div aria-label="Loading strategies" aria-busy="true" className="grid gap-4 md:grid-cols-2">
          <div className="h-44 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" />
          <div className="h-44 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" />
        </div>
      ) : (
        <SectionCard>
          <SectionCardHeader eyebrow="ADMIN-PUBLISHED" title="Available strategies" />
          {isError ? (
            <div className="p-5">
              <DataError message="Strategy availability could not be loaded. Please try again when the account service is available." />
            </div>
          ) : data?.length ? (
            <div className="grid divide-y divide-[var(--line)] md:grid-cols-2 md:divide-x md:divide-y-0">
              {data.map((strategy) => (
                <article key={strategy.id} className="p-5">
                  <div className="mb-5 flex items-center justify-between gap-4">
                    <span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
                      <FileCode2 size={17} />
                    </span>
                    {strategy.status && (
                      <span className={`rounded-md border px-2 py-1 font-mono text-[9px] uppercase tracking-[0.08em] ${
                        strategy.status === 'RUNNING' 
                          ? 'border-green-500/40 bg-green-500/10 text-green-600 dark:text-green-400'
                          : 'border-[var(--line)] text-[var(--ink-muted)]'
                      }`}>
                        {strategy.status}
                      </span>
                    )}
                  </div>
                  
                  <h2 className="text-[15px] font-semibold text-[var(--ink)]">{strategy.name}</h2>
                  <p className="mt-2 truncate font-mono text-[11px] text-[var(--ink-muted)]">
                    {strategy.scriptFileName || "Script details are restricted"}
                  </p>
                  <p className="mt-3 text-[12px] leading-5 text-[var(--ink-muted)]">
                    This strategy is made available and updated exclusively by an administrator.
                  </p>
                  
                  {strategy.scriptFileName && (
                    <div className="mt-5 flex items-center gap-2">
                      <a
                        href={`${API_BASE_URL}/api/v1/client/strategies/${strategy.id}/download`}
                        download
                        className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-strong)] bg-[var(--panel)] px-3 text-[12px] font-medium text-[var(--ink)] outline-none transition hover:border-[var(--accent)] hover:bg-[var(--panel-raised)] hover:text-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--focus)]"
                      >
                        <Download size={14} />
                        Download
                      </a>
                      <Link
                        href={`/dashboard/marketplace/view/${strategy.id}`}
                        className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--line-strong)] bg-[var(--panel)] px-3 text-[12px] font-medium text-[var(--ink)] outline-none transition hover:border-[var(--accent)] hover:bg-[var(--panel-raised)] hover:text-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--focus)]"
                      >
                        <Eye size={14} />
                        View Code
                      </Link>
                    </div>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <DataUnavailable message="No strategies have been published yet. Contact the administrator to upload strategies." />
          )}
        </SectionCard>
      )}
      
      <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] px-4 py-3.5 text-[12px] leading-5 text-[var(--ink-muted)]">
        <LockKeyhole size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" />
        <span>
          Python files are stored in the administrator workspace. You can view and download files for reference, but editing is restricted to administrators only.
        </span>
      </div>
    </div>
  );
}
