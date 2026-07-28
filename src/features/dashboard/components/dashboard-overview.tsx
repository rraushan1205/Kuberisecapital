"use client";

import { ArrowRight, Building2, FileCode2, ShieldCheck, Store } from "lucide-react";
import Link from "next/link";
import { DataError } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { TradingCalendar } from "@/components/trading-calendar/TradingCalendar";
import { useDashboardSnapshot } from "@/features/dashboard/hooks/use-dashboard-data";

function SnapshotValue({ label, value, detail }: { label: string; value?: string | number | null; detail?: string }) {
  const available = value !== null && value !== undefined && value !== "";
  return (
    <div className="min-w-0 px-5 py-4">
      <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">{label}</p>
      <p className="truncate text-[21px] font-semibold tracking-[-0.045em] text-[var(--ink)]">{available ? value : "—"}</p>
      <p className="mt-1 min-h-4 text-[11px] leading-4 text-[var(--ink-muted)]">{detail || (available ? "Current account data" : "Data not available")}</p>
    </div>
  );
}

function OverviewLoading() {
  return (
    <div className="space-y-5" aria-label="Loading dashboard data" aria-busy="true">
      <div className="h-14 w-64 animate-pulse rounded-lg bg-[var(--line)]" />
      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="h-60 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" />
        <div className="h-60 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" />
      </div>
      <div className="h-48 animate-pulse rounded-xl border border-[var(--line)] bg-[var(--panel)]" />
    </div>
  );
}

export function DashboardOverview() {
  const { data, isLoading, isError } = useDashboardSnapshot();
  if (isLoading) return <OverviewLoading />;

  const strategy = data?.strategy;
  const pnl = data?.pnl;
  const positions = data?.positions;
  const subscription = data?.subscription;
  const broker = data?.broker;
  const preferences = data?.preferences;

  return (
    <div className="space-y-5 lg:space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 font-mono text-[10px] font-medium tracking-[0.13em] text-[var(--accent)]">CLIENT WORKSPACE</p>
          <h1 className="text-[27px] font-semibold tracking-[-0.05em] text-[var(--ink)] sm:text-[31px]">Account overview</h1>
        </div>
        <p className="max-w-sm text-[12px] leading-5 text-[var(--ink-muted)]">Your account, strategy, and broker information in one controlled view.</p>
      </div>

      {isError && <DataError message="Dashboard data is unavailable. Existing values will appear when the account service reconnects." />}

      <div className="grid gap-4 lg:grid-cols-3">
  <SectionCard className="overflow-hidden lg:col-span-2">
    <SectionCardHeader
      eyebrow="JOURNAL"
      title="Trading P&L Calendar"
    />
    <div className="p-5">
      <TradingCalendar />
    </div>
  </SectionCard>

  <SectionCard>
    <SectionCardHeader
      eyebrow="PERFORMANCE"
      title="Profit & Loss"
    />

    <div className="grid divide-y divide-[var(--line)]">
      <SnapshotValue
        label="Daily P&L"
        value={pnl?.daily}
      />

      <SnapshotValue
        label="Overall P&L"
        value={pnl?.overall}
      />
    </div>
  </SectionCard>
</div>

      <SectionCard className="overflow-hidden">
        <SectionCardHeader eyebrow="NEXT STEPS" title="Account setup guidance" />
        <div className="grid divide-y divide-[var(--line)] md:grid-cols-3 md:divide-x md:divide-y-0">
          <Guidance icon={<Building2 size={16} />} title="Connect an approved broker" body="A broker connection is needed before your account can route orders." href="/dashboard/broker" />
          <Guidance icon={<Store size={16} />} title="Review marketplace availability" body="Strategies are published by an administrator and remain read-only here." href="/dashboard/marketplace" />
          <Guidance icon={<ShieldCheck size={16} />} title="Confirm account controls" body="Check your subscription, lot size, and risk settings before execution." href="/dashboard/settings" />
        </div>
      </SectionCard>
    </div>
  );
}

function CompactDatum({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex min-h-[68px] items-center justify-between gap-3 px-5 py-3.5">
      <p className="text-[12px] text-[var(--ink-muted)]">{label}</p>
      <p className="max-w-[52%] truncate text-right text-[12px] font-medium text-[var(--ink)]">{value || "Unavailable"}</p>
    </div>
  );
}

function Guidance({ icon, title, body, href }: { icon: React.ReactNode; title: string; body: string; href: string }) {
  return (
    <Link href={href} className="group block px-5 py-4 outline-none transition hover:bg-[var(--panel-raised)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus)]">
      <div className="mb-5 text-[var(--accent)]">{icon}</div>
      <p className="text-[13px] font-semibold text-[var(--ink)]">{title}</p>
      <p className="mt-1.5 text-[12px] leading-5 text-[var(--ink-muted)]">{body}</p>
      <span className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-medium text-[var(--accent)]">Open <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" /></span>
    </Link>
  );
}
