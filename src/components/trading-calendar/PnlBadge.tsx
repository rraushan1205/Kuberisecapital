import { cn } from "@/lib/utils";

interface PnlBadgeProps {
  pnl: number;
  className?: string;
  showIcon?: boolean;
}

export function formatINR(val: number): string {
  const isNegative = val < 0;
  const absVal = Math.abs(val);
  
  // Format to Indian Rupee standard
  const formatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });
  
  const formatted = formatter.format(absVal);
  return `${isNegative ? "-" : "+"}${formatted}`;
}

export function PnlBadge({ pnl, className, showIcon = false }: PnlBadgeProps) {
  const isPositive = pnl > 0;
  const isNegative = pnl < 0;

  let textClass = "text-[var(--ink-muted)]";
  let bgClass = "bg-[var(--panel-raised)]";
  
  if (isPositive) {
    textClass = "text-[#10b981] font-semibold"; // Green
    bgClass = "bg-[#10b981]/10";
  } else if (isNegative) {
    textClass = "text-[#ef4444] font-semibold"; // Red
    bgClass = "bg-[#ef4444]/10";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium transition-all",
        textClass,
        bgClass,
        className
      )}
    >
      {showIcon && isPositive && <span className="mr-1">▲</span>}
      {showIcon && isNegative && <span className="mr-1">▼</span>}
      {pnl === 0 ? "₹0" : formatINR(pnl)}
    </span>
  );
}
