import Link from "next/link";

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/login" className="group inline-flex items-center gap-2.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)]" aria-label="Stratum secure access">
      <span className="relative grid h-7 w-7 shrink-0 place-items-center rounded-[7px] bg-[var(--ink)] transition-transform duration-200 group-hover:-translate-y-px">
        <span className="h-3.5 w-3.5 rounded-[3px] border-2 border-[var(--panel)]" />
        <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-sm bg-[var(--accent)]" />
      </span>
      {!compact && <span className="text-[15px] font-semibold tracking-[-0.03em] text-[var(--ink)]">Stratum</span>}
    </Link>
  );
}
