"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Bell, ClipboardList, FileCode2, LayoutDashboard, LogOut, Menu, RadioTower, ShieldCheck, Users, UserRoundCheck, UserRoundPlus, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { adminApi } from "@/features/admin/api/admin-api";
import { useAdminSession } from "@/features/admin/hooks/use-admin-data";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/admin/users", label: "User management", icon: Users },
  { href: "/admin/pending-registrations", label: "Pending registrations", icon: UserRoundPlus },
  { href: "/admin/subscriptions", label: "Subscription approval", icon: UserRoundCheck },
  { href: "/admin/connected-users", label: "Connected users", icon: RadioTower },
  { href: "/admin/strategies", label: "Strategies", icon: FileCode2 },
  { href: "/admin/logs", label: "Execution logs", icon: ClipboardList },
  { href: "/admin/announcements", label: "Announcements", icon: Bell },
];

function AdminIdentity() {
  return <Link href="/admin/dashboard" className="flex items-center gap-2.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)]"><span className="grid h-7 w-7 place-items-center rounded-[7px] bg-[var(--danger)] text-[11px] font-bold text-white">S</span><span><span className="block text-[14px] font-semibold tracking-[-0.03em] text-[var(--ink)]">Stratum</span><span className="block font-mono text-[8px] font-medium tracking-[0.13em] text-[var(--danger)]">ADMIN PORTAL</span></span></Link>;
}

function AdminNavigation({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return <nav aria-label="Admin navigation" className="flex flex-1 flex-col gap-1 px-3 py-5"><p className="mb-2 px-2 font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--ink-subtle)]">CONTROL</p>{navigation.map(({ href, label, icon: Icon, exact }) => { const active = exact ? pathname === href : pathname.startsWith(href); return <Link key={href} href={href} onClick={onNavigate} className={cn("flex min-h-10 items-center gap-3 rounded-lg px-2.5 text-[12px] outline-none transition focus-visible:ring-2 focus-visible:ring-[var(--focus)]", active ? "bg-[var(--danger-soft)] text-[var(--ink)]" : "text-[var(--ink-muted)] hover:bg-[var(--panel-raised)] hover:text-[var(--ink)]")}><Icon size={16} strokeWidth={active ? 2 : 1.7} className={active ? "text-[var(--danger)]" : "text-[var(--ink-subtle)]"} /><span className="font-medium">{label}</span></Link>; })}</nav>;
}

function AdminHeader({ onOpenNavigation }: { onOpenNavigation: () => void }) {
  const { data, isLoading } = useAdminSession();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  async function logout() {
    setIsLoggingOut(true);
    try { await adminApi.logout(); } finally { router.replace("/admin/login"); }
  }
  return <header className="flex min-h-[73px] items-center justify-between gap-4 border-b border-[var(--line)] bg-[var(--canvas)] px-4 sm:px-6 lg:px-8"><div className="flex items-center gap-3 lg:hidden"><Button size="icon" variant="quiet" onClick={onOpenNavigation} aria-label="Open admin navigation"><Menu size={19} /></Button><span className="font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--danger)]">SUPER ADMIN</span></div><div className="ml-auto flex items-center gap-2 sm:gap-3"><div className="hidden border-r border-[var(--line)] pr-4 text-right sm:block"><p className="font-mono text-[9px] font-medium uppercase tracking-[0.1em] text-[var(--ink-subtle)]">Authenticated as</p><p className="mt-0.5 max-w-56 truncate text-[12px] font-medium text-[var(--ink)]">{isLoading ? "Loading" : data?.email || "Session unavailable"}</p></div><ThemeToggle /><Button variant="quiet" size="sm" onClick={logout} disabled={isLoggingOut} aria-label="Log out of Admin Portal"><LogOut size={15} /><span className="hidden sm:inline">Log out</span></Button></div></header>;
}

export function AdminShell({ children }: { children: ReactNode }) {
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const reducedMotion = useReducedMotion();
  const sidebar = <><div className="flex h-[73px] items-center border-b border-[var(--line)] px-5"><AdminIdentity /></div><AdminNavigation onNavigate={() => setMobileNavigationOpen(false)} /><div className="mx-3 mb-4 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] p-3"><div className="mb-2 flex items-center gap-2 text-[var(--danger)]"><ShieldCheck size={14} /><span className="font-mono text-[10px] tracking-[0.1em]">RBAC ENFORCED</span></div><p className="text-[11px] leading-4 text-[var(--ink-muted)]">Protected actions are checked by the API for every request.</p></div></>;
  return <div className="min-h-dvh bg-[var(--canvas)] lg:grid lg:grid-cols-[252px_minmax(0,1fr)]"><aside className="fixed inset-y-0 left-0 z-20 hidden w-[252px] flex-col border-r border-[var(--line)] bg-[var(--side-panel)] lg:flex">{sidebar}</aside><AnimatePresence>{mobileNavigationOpen && <motion.div initial={reducedMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 bg-[#071015]/35 lg:hidden"><motion.aside initial={reducedMotion ? false : { x: -24 }} animate={{ x: 0 }} exit={{ x: -24 }} transition={{ duration: 0.16 }} className="flex h-full w-[min(304px,86vw)] flex-col border-r border-[var(--line)] bg-[var(--side-panel)] shadow-2xl"><div className="absolute right-3 top-3"><Button size="icon" variant="quiet" onClick={() => setMobileNavigationOpen(false)} aria-label="Close admin navigation"><X size={18} /></Button></div>{sidebar}</motion.aside><button type="button" aria-label="Close admin navigation" className="absolute inset-y-0 left-[min(304px,86vw)] right-0" onClick={() => setMobileNavigationOpen(false)} /></motion.div>}</AnimatePresence><div className="min-w-0 lg:col-start-2"><AdminHeader onOpenNavigation={() => setMobileNavigationOpen(true)} /><main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main></div></div>;
}
