"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ArrowUpRight, LockKeyhole } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";

type AuthShellProps = {
  children: React.ReactNode;
  mode?: "access" | "enrollment" | "status";
};

const sideCopy = {
  access: {
    eyebrow: "SECURE WORKSPACE",
    title: "Execution starts with certainty.",
    body: "A disciplined environment for subscribed participants and the teams that support them.",
  },
  enrollment: {
    eyebrow: "MEMBER ENROLLMENT",
    title: "A measured path to access.",
    body: "Every account is verified and reviewed before it joins the execution environment.",
  },
  status: {
    eyebrow: "ACCOUNT CONTROL",
    title: "Access is considered, not automatic.",
    body: "We keep account status clear, deliberate, and visible at every step.",
  },
};

export function AuthShell({ children, mode = "access" }: AuthShellProps) {
  const reducedMotion = useReducedMotion();
  const pathname = usePathname();
  const contentAnimation = reducedMotion
    ? undefined
    : { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] as const } };
  const copy = sideCopy[mode];
  const isRegister = pathname === "/register";

  return (
    <main className="min-h-dvh bg-[var(--canvas)] lg:grid lg:grid-cols-[minmax(370px,0.94fr)_minmax(560px,1.35fr)]">
      <aside className="relative hidden overflow-hidden border-r border-[var(--line)] bg-[var(--side-panel)] px-9 py-8 lg:flex lg:min-h-dvh lg:flex-col xl:px-12">
        <div className="absolute inset-0 opacity-[0.42] [background-image:linear-gradient(to_right,var(--line)_1px,transparent_1px),linear-gradient(to_bottom,var(--line)_1px,transparent_1px)] [background-size:48px_48px]" />
        <div className="relative flex items-center justify-between">
          <BrandMark />
          <span className="rounded-full border border-[var(--line-strong)] px-2.5 py-1 font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--ink-muted)]">EST. 2018</span>
        </div>
        <div className="relative my-auto max-w-md pb-14 pt-20">
          <p className="mb-5 font-mono text-[11px] font-medium tracking-[0.14em] text-[var(--accent)]">{copy.eyebrow}</p>
          <h1 className="max-w-[12ch] text-[clamp(2.5rem,4vw,4.25rem)] font-semibold leading-[0.97] tracking-[-0.065em] text-[var(--ink)]">{copy.title}</h1>
          <p className="mt-7 max-w-[38ch] text-[15px] leading-6 text-[var(--ink-muted)]">{copy.body}</p>
        </div>
        <div className="relative grid grid-cols-2 gap-3 border-t border-[var(--line-strong)] pt-5">
          <div className="rounded-lg border border-[var(--line)] bg-[color-mix(in_srgb,var(--panel)_65%,transparent)] p-3.5">
            <div className="mb-6 flex items-center gap-2 text-[var(--ink-muted)]"><Activity size={14} /><span className="font-mono text-[10px] tracking-[0.1em]">SYSTEMS</span></div>
            <div className="flex items-center gap-2 text-xs font-medium text-[var(--ink)]"><span className="h-1.5 w-1.5 animate-soft-pulse rounded-full bg-[var(--positive)]" />Operational</div>
          </div>
          <div className="rounded-lg border border-[var(--line)] bg-[color-mix(in_srgb,var(--panel)_65%,transparent)] p-3.5">
            <div className="mb-6 flex items-center gap-2 text-[var(--ink-muted)]"><LockKeyhole size={14} /><span className="font-mono text-[10px] tracking-[0.1em]">ACCESS</span></div>
            <div className="text-xs font-medium text-[var(--ink)]">Encrypted session</div>
          </div>
        </div>
      </aside>

      <section className="relative flex min-h-dvh flex-col px-5 py-5 sm:px-8 sm:py-7 lg:px-12 lg:py-8 xl:px-16">
        <header className="flex items-center justify-between lg:justify-end">
          <div className="lg:hidden"><BrandMark /></div>
          <ThemeToggle />
        </header>
        <motion.div {...contentAnimation} className="mx-auto flex w-full max-w-[440px] flex-1 flex-col justify-center py-10 lg:py-12">
          {children}
        </motion.div>
        <footer className="flex min-h-6 items-center justify-between gap-4 font-mono text-[10px] tracking-[0.04em] text-[var(--ink-subtle)]">
          <span>© {new Date().getFullYear()} STRATUM SYSTEMS</span>
          {!isRegister && <Link href="/register" className="group inline-flex items-center gap-1.5 rounded-sm outline-none transition hover:text-[var(--ink-muted)] focus-visible:ring-2 focus-visible:ring-[var(--focus)]">REQUEST ACCESS <ArrowUpRight size={12} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" /></Link>}
        </footer>
      </section>
    </main>
  );
}
