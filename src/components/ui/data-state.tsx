import { AlertCircle, Inbox } from "lucide-react";

export function DataUnavailable({ compact = false, message = "This information is not available yet." }: { compact?: boolean; message?: string }) {
  return (
    <div className={compact ? "flex items-center gap-2 text-xs text-[var(--ink-muted)]" : "flex min-h-28 flex-col items-center justify-center px-5 py-7 text-center"}>
      {!compact && <Inbox size={19} className="mb-2 text-[var(--ink-subtle)]" />}
      <p className={compact ? "" : "text-sm text-[var(--ink-muted)]"}>{message}</p>
    </div>
  );
}

export function DataError({ message = "We couldn’t load the latest account data." }: { message?: string }) {
  return (
    <div role="status" className="flex items-start gap-2.5 rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3.5 py-3 text-[12px] leading-5 text-[var(--danger)]">
      <AlertCircle size={16} className="mt-0.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
