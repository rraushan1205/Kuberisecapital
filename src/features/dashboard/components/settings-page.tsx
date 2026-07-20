"use client";

import { Palette, ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { DataError } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { useDashboardSnapshot } from "@/features/dashboard/hooks/use-dashboard-data";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";

export function SettingsPage() {
  const { data, isLoading, isError } = useDashboardSnapshot();
  return (
    <div>
      <WorkspacePageTitle eyebrow="SETTINGS" title="Workspace settings">Appearance is managed locally. Trading and account controls are displayed from the account service.</WorkspacePageTitle>
      {isError && <div className="mb-4"><DataError message="Account settings are unavailable. No account controls can be changed from this view." /></div>}
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <SectionCard>
          <SectionCardHeader eyebrow="APPEARANCE" title="Theme" />
          <div className="flex items-center justify-between gap-4 p-5"><div><div className="mb-2 flex items-center gap-2 text-[var(--accent)]"><Palette size={16} /><span className="font-mono text-[10px] tracking-[0.11em]">DISPLAY</span></div><p className="text-[12px] leading-5 text-[var(--ink-muted)]">Choose a theme that suits your workspace.</p></div><ThemeToggle /></div>
        </SectionCard>
        <SectionCard>
          <SectionCardHeader eyebrow="ACCOUNT CONTROLS" title="Trading preferences" />
          <div className="grid divide-y divide-[var(--line)] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            <ReadOnlyValue label="Lot size" value={data?.preferences?.lotSize} loading={isLoading} />
            <ReadOnlyValue label="Risk settings" value={data?.preferences?.riskSettings} loading={isLoading} />
          </div>
        </SectionCard>
      </div>
      <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] px-4 py-3.5 text-[12px] leading-5 text-[var(--ink-muted)]"><ShieldCheck size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" /> <span>Strategy configuration and Python files are controlled by the administrator. This view does not permit strategy edits.</span></div>
    </div>
  );
}

function ReadOnlyValue({ label, value, loading }: { label: string; value?: string | null; loading: boolean }) {
  return <div className="px-5 py-4"><p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">{label}</p>{loading ? <span className="block h-5 w-28 animate-pulse rounded bg-[var(--line)]" /> : <p className="text-[14px] font-medium text-[var(--ink)]">{value || "Unavailable"}</p>}<p className="mt-1.5 text-[11px] leading-4 text-[var(--ink-muted)]">Read from the approved account configuration.</p></div>;
}
