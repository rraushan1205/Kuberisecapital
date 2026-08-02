import { CalendarDaySummary } from "@/types/calendar";
import { cn } from "@/lib/utils";

interface CalendarDayProps {
  day: number;
  dateStr: string;
  isCurrentMonth: boolean;
  isToday: boolean;
  summary?: CalendarDaySummary;
  onClick?: () => void;
}

export function CalendarDay({
  day,
  dateStr,
  isCurrentMonth,
  isToday,
  summary,
  onClick,
}: CalendarDayProps) {
  const hasTrades = summary && summary.trades > 0;
  const pnl = summary?.pnl;
  const isPositive = pnl !== undefined && pnl > 0;
  const isNegative = pnl !== undefined && pnl < 0;

  const isClickable = isCurrentMonth && hasTrades;

  // Color mapping for day numbers based on P&L magnitude
  let numberColor = "text-[var(--ink-subtle)] opacity-50 font-normal"; // Default muted for no activity

  if (!isCurrentMonth) {
    // Previous/next month days - very faded
    numberColor = "text-[var(--ink-subtle)] opacity-30 font-normal";
  } else if (isCurrentMonth && hasTrades && pnl !== undefined) {
    // Current month with actual trading activity
    const absPnl = Math.abs(pnl);
    
    if (isPositive) {
      // Green shades for profit - 3 tiers
      if (absPnl >= 50000) {
        numberColor = "text-[#10b981] font-bold"; // High profit - bright green
      } else if (absPnl >= 20000) {
        numberColor = "text-[#34d399] font-semibold"; // Medium profit
      } else {
        numberColor = "text-[#6ee7b7] font-medium"; // Low profit
      }
    } else if (isNegative) {
      // Red shades for loss - 3 tiers
      if (absPnl >= 50000) {
        numberColor = "text-[#ef4444] font-bold"; // High loss - bright red
      } else if (absPnl >= 20000) {
        numberColor = "text-[#f87171] font-semibold"; // Medium loss
      } else {
        numberColor = "text-[#fca5a5] font-medium"; // Low loss
      }
    }
  }
  // else: stays as default muted color for current month days with no trades

  return (
    <button
      type="button"
      onClick={isClickable ? onClick : undefined}
      disabled={!isClickable}
      className={cn(
        "relative w-[22px] h-[22px] flex items-center justify-center transition-colors duration-150 rounded-sm",
        isToday && "ring-[1px] ring-[var(--accent)] ring-inset",
        isClickable
          ? "cursor-pointer hover:bg-[var(--line)]/30"
          : "cursor-default"
      )}
      aria-label={
        isCurrentMonth
          ? hasTrades && pnl !== undefined
            ? `Day ${day}, ${isPositive ? "profit" : "loss"} ${Math.abs(pnl).toFixed(0)}`
            : `Day ${day}, no trades`
          : undefined
      }
    >
      <span className={cn("text-[9px] tabular-nums leading-none", numberColor)}>
        {day}
      </span>
    </button>
  );
}
