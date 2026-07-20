import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function SectionCard({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("rounded-xl border border-[var(--line)] bg-[var(--panel)]", className)}>{children}</section>;
}

export function SectionCardHeader({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-[var(--line)] px-5 py-4">
      <div>
        {eyebrow && <p className="mb-1 font-mono text-[10px] font-medium tracking-[0.11em] text-[var(--ink-subtle)]">{eyebrow}</p>}
        <h2 className="text-sm font-semibold tracking-[-0.015em] text-[var(--ink)]">{title}</h2>
      </div>
      {action}
    </div>
  );
}
