import type { ReactNode } from "react";

export function AdminPageTitle({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-6 max-w-2xl">
      {eyebrow && (
        <p className="mb-2 font-mono text-[10px] font-medium tracking-[0.13em] text-[var(--danger)]">{eyebrow}</p>
      )}
      <h1 className="text-[27px] font-semibold tracking-[-0.05em] text-[var(--ink)] sm:text-[31px]">{title}</h1>
      {(description || children) && (
        <p className="mt-2.5 text-[13px] leading-6 text-[var(--ink-muted)]">{description || children}</p>
      )}
    </div>
  );
}