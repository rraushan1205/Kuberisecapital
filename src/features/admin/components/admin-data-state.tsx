import { AlertCircle, Inbox } from "lucide-react";

export function AdminLoadingRows({ rows = 4 }: { rows?: number }) {
  return <div aria-label="Loading data" aria-busy="true" className="divide-y divide-[var(--line)]">{Array.from({ length: rows }, (_, index) => <div key={index} className="h-14 animate-pulse bg-[var(--panel)]" />)}</div>;
}

export function AdminEmpty({ message }: { message: string }) {
  return <div className="flex min-h-40 flex-col items-center justify-center px-5 py-8 text-center"><Inbox size={19} className="mb-2 text-[var(--ink-subtle)]" /><p className="text-[13px] text-[var(--ink-muted)]">{message}</p></div>;
}

export function AdminError({ message }: { message: string }) {
  return <div role="alert" className="flex items-start gap-2.5 rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3.5 py-3 text-[12px] leading-5 text-[var(--danger)]"><AlertCircle size={16} className="mt-0.5 shrink-0" />{message}</div>;
}

type AdminDataStateProps = {
  state: "loading" | "empty" | "error";
  emptyMessage?: string;
  errorMessage?: string;
  rows?: number;
};

export function AdminDataState({ state, emptyMessage = "No data available", errorMessage = "Failed to load data", rows = 4 }: AdminDataStateProps) {
  if (state === "loading") {
    return <AdminLoadingRows rows={rows} />;
  }
  if (state === "empty") {
    return <AdminEmpty message={emptyMessage} />;
  }
  if (state === "error") {
    return <AdminError message={errorMessage} />;
  }
  return null;
}
