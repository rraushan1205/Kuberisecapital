"use client";

import { ArrowRight, TrendingUp, TrendingDown, CircleAlert, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { useDashboardSnapshot, usePositions, useExecutionLogs, usePnlChartData } from "@/features/dashboard/hooks/use-dashboard-data";
import type { Position, ExecutionLog } from "@/features/dashboard/lib/mock-data";

function SnapshotValue({ label, value, detail, trend }: { label: string; value?: string | number | null; detail?: string; trend?: string }) {
  const available = value !== null && value !== undefined && value !== "";
  return (
    <div className="min-w-0 px-5 py-4">
      <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">{label}</p>
      <div className="flex items-baseline gap-2">
        <p className="truncate text-[21px] font-semibold tracking-[-0.045em] text-[var(--ink)]">{available ? value : "—"}</p>
        {trend && <span className="text-[12px] font-medium text-green-500">{trend}</span>}
      </div>
      <p className="mt-1 min-h-4 text-[11px] leading-4 text-[var(--ink-muted)]">{detail || (available ? "Current account data" : "Data not available")}</p>
    </div>
  );
}

function MiniSparkline({ data, color = "rgb(34, 197, 94)" }: { data: Array<{ value: number }>; color?: string }) {
  if (!data || data.length === 0) return null;
  
  const values = data.map(d => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * 100;
    const y = 100 - ((value - min) / range) * 100;
    return `${x},${y}`;
  }).join(" ");
  
  return (
    <svg className="h-12 w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
        opacity="0.8"
      />
    </svg>
  );
}

function PositionRow({ position }: { position: Position }) {
  const isProfit = position.pnl > 0;
  
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--line)] px-5 py-3 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-[var(--ink)] truncate">{position.symbol}</p>
        <p className="text-[11px] text-[var(--ink-muted)] mt-0.5">
          {position.type} · {position.quantity} qty
        </p>
      </div>
      <div className="text-right">
        <p className={`text-[13px] font-semibold ${isProfit ? "text-green-500" : "text-red-500"}`}>
          {isProfit ? "+" : ""}₹{position.pnl.toFixed(2)}
        </p>
        <p className={`text-[11px] font-medium ${isProfit ? "text-green-500/70" : "text-red-500/70"}`}>
          {isProfit ? "+" : ""}{position.pnlPercent.toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

function ExecutionLogRow({ log }: { log: ExecutionLog }) {
  const statusColors = {
    Filled: "text-green-500",
    Executed: "text-blue-500",
    Info: "text-[var(--ink-muted)]",
    Warning: "text-yellow-500",
    Failed: "text-red-500",
  };
  
  return (
    <div className="flex items-start justify-between gap-4 border-b border-[var(--line)] px-5 py-3 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] font-mono text-[var(--ink-subtle)]">{log.timestamp}</span>
          <span className={`text-[11px] font-medium ${statusColors[log.status]}`}>{log.status}</span>
        </div>
        <p className="text-[13px] text-[var(--ink)]">{log.message}</p>
        {log.details && <p className="text-[11px] text-[var(--ink-muted)] mt-1">{log.details}</p>}
      </div>
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

export function DashboardOverviewEnhanced() {
  const { data: snapshot, isLoading: snapshotLoading } = useDashboardSnapshot();
  const { data: positions, isLoading: positionsLoading } = usePositions();
  const { data: logs, isLoading: logsLoading } = useExecutionLogs();
  const { data: chartData } = usePnlChartData();
  
  if (snapshotLoading) return <OverviewLoading />;

  const strategy = snapshot?.strategy;
  const pnl = snapshot?.pnl;
  const positionStats = snapshot?.positions;
  const subscription = snapshot?.subscription;
  const broker = snapshot?.broker;
  const preferences = snapshot?.preferences;

  return (
    <div className="space-y-5 lg:space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 font-mono text-[10px] font-medium tracking-[0.13em] text-[var(--accent)]">CLIENT WORKSPACE</p>
          <h1 className="text-[27px] font-semibold tracking-[-0.05em] text-[var(--ink)] sm:text-[31px]">Account overview</h1>
        </div>
        <p className="max-w-sm text-[12px] leading-5 text-[var(--ink-muted)]">Your account, strategy, and broker information in one controlled view.</p>
      </div>

      {/* Demo Mode Banner */}
      <div className="flex items-center gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3">
        <CircleAlert size={18} className="shrink-0 text-yellow-500" />
        <div className="flex-1">
          <p className="text-[13px] font-medium text-[var(--ink)]">Educational demo mode</p>
          <p className="text-[12px] text-[var(--ink-muted)] mt-0.5">
            Figures below are simulated on delayed NSE data — no real orders are placed while demo mode is on.
          </p>
        </div>
        <span className="rounded-md border border-yellow-500/40 bg-yellow-500/20 px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-wider text-yellow-600 dark:text-yellow-400">
          GO LIVE
        </span>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        {/* Strategy Status */}
        <SectionCard>
          <SectionCardHeader eyebrow="STRATEGY" title="Strategy status" action={<Link href="/dashboard/marketplace" className="inline-flex items-center gap-1.5 rounded-md text-[12px] font-medium text-[var(--accent)] outline-none transition hover:text-[var(--accent-strong)] focus-visible:ring-2 focus-visible:ring-[var(--focus)]">Marketplace <ArrowRight size={14} /></Link>} />
          <div className="grid divide-y divide-[var(--line)] sm:grid-cols-[1.2fr_0.8fr] sm:divide-x sm:divide-y-0">
            <div className="px-5 py-5">
              <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">Selected strategy</p>
              <p className="text-[19px] font-semibold tracking-[-0.035em] text-[var(--ink)]">{strategy?.selectedName || "No strategy selected"}</p>
              <p className="mt-2 text-[12px] leading-5 text-[var(--ink-muted)]">
                {strategy?.status ? (
                  <>
                    NIFTY & BANKNIFTY options · Intraday · Risk tier: <span className="text-[var(--ink)]">Moderate</span>
                  </>
                ) : (
                  "An administrator publishes available strategy access."
                )}
              </p>
            </div>
            <div className="px-5 py-5">
              <div className="mb-2 flex items-center gap-2 text-[var(--ink-subtle)]">
                <div className="rounded bg-[var(--accent-soft)] p-1.5 text-[var(--accent)]">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="16 18 22 12 16 6" />
                    <polyline points="8 6 2 12 8 18" />
                  </svg>
                </div>
                <span className="font-mono text-[10px] font-medium uppercase tracking-[0.11em]">Python script</span>
              </div>
              <p className="truncate text-[13px] font-medium text-[var(--ink)]">{strategy?.scriptFileName || "Not assigned"}</p>
              <p className="mt-2 text-[11px] leading-4 text-[var(--ink-muted)]">
                Running · last execution 2 min ago · admin-managed, not editable here
              </p>
            </div>
          </div>
        </SectionCard>

        {/* Profit & Loss */}
        <SectionCard>
          <SectionCardHeader eyebrow="PERFORMANCE" title="Profit & loss" />
          <div className="grid divide-x divide-[var(--line)] sm:grid-cols-2">
            <div className="px-5 py-4">
              <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">Daily P&L</p>
              <div className="flex items-baseline gap-2">
                <TrendingUp size={16} className="text-green-500" />
                <p className="text-[21px] font-semibold tracking-[-0.045em] text-[var(--ink)]">{pnl?.daily || "—"}</p>
              </div>
              <p className="mt-1 text-[11px] leading-4 text-green-500 font-medium">+1.8% on deployed capital</p>
              {chartData?.daily && <div className="mt-3"><MiniSparkline data={chartData.daily} /></div>}
            </div>
            <div className="px-5 py-4">
              <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">Overall P&L</p>
              <div className="flex items-baseline gap-2">
                <TrendingUp size={16} className="text-green-500" />
                <p className="text-[21px] font-semibold tracking-[-0.045em] text-[var(--ink)]">{pnl?.overall || "—"}</p>
              </div>
              <p className="mt-1 text-[11px] leading-4 text-green-500 font-medium">+12.4% since Feb 2026</p>
              {chartData?.overall && <div className="mt-3"><MiniSparkline data={chartData.overall} /></div>}
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        {/* Position Status */}
        <SectionCard>
          <SectionCardHeader eyebrow="POSITIONS" title="Position status" />
          <div className="grid divide-x divide-[var(--line)] sm:grid-cols-2">
            <div className="px-5 py-4">
              <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">Open positions</p>
              <p className="text-[32px] font-bold tracking-[-0.045em] text-[var(--ink)]">{positionStats?.open ?? "—"}</p>
              <p className="mt-1 text-[11px] leading-4 text-[var(--ink-muted)]">
                NIFTY 24800 CE · BANKNIFTY 53000 PE · RELIANCE FUT
              </p>
            </div>
            <div className="px-5 py-4">
              <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">Closed positions</p>
              <p className="text-[32px] font-bold tracking-[-0.045em] text-[var(--ink)]">{positionStats?.closed ?? "—"}</p>
              <p className="mt-1 text-[11px] leading-4 text-[var(--ink-muted)]">
                Today · win rate 68% (18W / 9L)
              </p>
            </div>
          </div>
        </SectionCard>

        {/* Account Configuration */}
        <SectionCard>
          <SectionCardHeader eyebrow="ACCOUNT CONFIGURATION" title="Subscription, broker & risk" />
          <div className="grid divide-y divide-[var(--line)] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            <div className="divide-y divide-[var(--line)]">
              <CompactDatum label="Subscription status" value={subscription?.status} highlight />
              <CompactDatum label="Lot size" value={preferences?.lotSize} />
            </div>
            <div className="divide-y divide-[var(--line)]">
              <CompactDatum label="Broker connection" value={broker?.provider ? `${broker.provider} · ${broker.status}` : "Not connected"} highlight />
              <CompactDatum label="Risk settings" value={preferences?.riskSettings} />
            </div>
          </div>
        </SectionCard>
      </div>

      {/* Open Positions Detail */}
      {!positionsLoading && positions?.open && positions.open.length > 0 && (
        <SectionCard>
          <SectionCardHeader eyebrow="POSITIONS" title="Position status" action={<span className="text-[12px] font-medium text-[var(--accent)]">3 open · 27 closed today</span>} />
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="px-5 py-3 border-b border-[var(--line)]">
                <p className="font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">Open positions</p>
              </div>
              {positions.open.map((position) => (
                <PositionRow key={position.id} position={position} />
              ))}
            </div>
            <div>
              <div className="px-5 py-3 border-b border-[var(--line)]">
                <p className="font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">Closed positions</p>
              </div>
              {positions.closed && positions.closed.slice(0, 3).map((position) => (
                <PositionRow key={position.id} position={position} />
              ))}
            </div>
          </div>
        </SectionCard>
      )}

      {/* Execution Logs */}
      {!logsLoading && logs && logs.length > 0 && (
        <SectionCard>
          <SectionCardHeader 
            eyebrow="ACTIVITY" 
            title="Recent execution log" 
            action={
              <Link href="/dashboard/logs" className="inline-flex items-center gap-1.5 rounded-md text-[12px] font-medium text-[var(--accent)] outline-none transition hover:text-[var(--accent-strong)] focus-visible:ring-2 focus-visible:ring-[var(--focus)]">
                View all <ArrowRight size={14} />
              </Link>
            } 
          />
          <div className="max-h-80 overflow-y-auto">
            {logs.slice(0, 5).map((log) => (
              <ExecutionLogRow key={log.id} log={log} />
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

function CompactDatum({ label, value, highlight }: { label: string; value?: string | null; highlight?: boolean }) {
  return (
    <div className="flex min-h-[68px] items-center justify-between gap-3 px-5 py-3.5">
      <p className="text-[12px] text-[var(--ink-muted)]">{label}</p>
      <p className={`max-w-[52%] truncate text-right text-[12px] font-medium ${highlight ? "text-green-500" : "text-[var(--ink)]"}`}>
        {value || "Unavailable"}
      </p>
    </div>
  );
}
