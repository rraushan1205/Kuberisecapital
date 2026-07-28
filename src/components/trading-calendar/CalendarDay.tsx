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
  const pnl = summary?.pnl ?? 0;
  const isPositive = pnl > 0;
  const isNegative = pnl < 0;

  // Color is the only signal — no text inside cells
  let cellColor = "bg-[#232a35]";

  if (hasTrades) {
    if (isPositive) {
      cellColor = "bg-[#1d4736]";
    } else if (isNegative) {
      cellColor = "bg-[#4a2628]";
    }
  } else if (!isCurrentMonth) {
    cellColor = "bg-transparent";
  }

  const isClickable = isCurrentMonth && hasTrades;

  return (
  <button
    type="button"
    onClick={isClickable ? onClick : undefined}
    disabled={!isClickable}
    className={cn(
      "relative aspect-square w-full rounded-xl transition-all duration-200 flex items-center justify-center",
      cellColor,
      isToday
        ? "ring-2 ring-[var(--accent)]"
        : "",
      isClickable
        ? "cursor-pointer hover:scale-105 hover:shadow-lg"
        : "cursor-default"
    )}
    aria-label={
      isCurrentMonth
        ? hasTrades
          ? `Day ${day}`
          : `Day ${day}`
        : undefined
    }
  >
    <span
      className={cn(
        "text-sm font-semibold",
        isCurrentMonth
          ? "text-white"
          : "text-[var(--ink-subtle)]"
      )}
    >
      {day} 
    </span>
  </button>
);  
}