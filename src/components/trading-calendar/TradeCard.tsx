import { Trade } from "@/types/calendar";
import { PnlBadge } from "./PnlBadge";
import { cn } from "@/lib/utils";

interface TradeCardProps {
  trade: Trade;
}

export function TradeCard({ trade }: TradeCardProps) {
  const isBuy = trade.side === "BUY";
  
  return (
    <div className="relative overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--panel)] p-4 transition-all hover:border-[var(--line-strong)] hover:bg-[var(--panel-raised)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {/* Side Indicator */}
          <span
            className={cn(
              "inline-flex items-center justify-center rounded-md px-2.5 py-1 text-[11px] font-semibold tracking-wide uppercase",
              isBuy
                ? "bg-[#10b981]/10 text-[#10b981] border border-[#10b981]/20"
                : "bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/20"
            )}
          >
            {trade.side}
          </span>
          <div>
            <h4 className="text-sm font-semibold tracking-tight text-[var(--ink)]">
              {trade.symbol}
            </h4>
            <p className="text-[11px] text-[var(--ink-muted)]">
              Qty: <span className="font-medium text-[var(--ink)]">{trade.quantity}</span>
            </p>
          </div>
        </div>

        {/* Pnl & Timing */}
        <div className="flex items-center gap-4 sm:gap-6">
          <div className="text-right">
            <p className="font-mono text-[11px] text-[var(--ink-muted)]">
              {trade.entryTime} - {trade.exitTime}
            </p>
            <p className="text-[10px] uppercase tracking-wider text-[var(--ink-subtle)] font-mono mt-0.5">
              Execution Time (IST)
            </p>
          </div>
          <div className="min-w-[90px] text-right">
            <PnlBadge pnl={trade.pnl} showIcon className="text-xs" />
          </div>
        </div>
      </div>
    </div>
  );
}
