"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { BarChart3, Building2, ChevronDown, CircleHelp, LayoutDashboard, LogOut, Menu, Settings2, Store } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { BrandMark } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useDashboardSnapshot } from "@/features/dashboard/hooks/use-dashboard-data";
import { useDashboardUiStore } from "@/features/dashboard/store/dashboard-ui-store";
import { MarketTicker } from "@/features/dashboard/components/market-ticker";
import { logout } from "@/lib/auth-client";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/marketplace", label: "Marketplace", icon: Store, note: "Strategies" },
  { href: "/dashboard/broker", label: "Broker", icon: Building2 },
  { href: "/dashboard/support", label: "Support", icon: CircleHelp },
  { href: "/dashboard/settings", label: "Settings", icon: Settings2 },
];

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary navigation" className="flex flex-1 flex-col gap-1 px-3 py-5">
      <p className="mb-2 px-2 font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--ink-subtle)]">WORKSPACE</p>
      {navigation.map(({ href, label, icon: Icon, note, exact }) => {
        const active = exact ? pathname === href : pathname.startsWith(href);
        return (
          <Link key={href} href={href} onClick={onNavigate} className={cn("group flex min-h-10 items-center gap-3 rounded-lg px-2.5 text-[13px] outline-none transition focus-visible:ring-2 focus-visible:ring-[var(--focus)]", active ? "bg-[var(--accent-soft)] text-[var(--ink)]" : "text-[var(--ink-muted)] hover:bg-[var(--panel-raised)] hover:text-[var(--ink)]")}>
            <Icon size={17} strokeWidth={active ? 2 : 1.7} className={active ? "text-[var(--accent)]" : "text-[var(--ink-subtle)]"} />
            <span className="font-medium">{label}</span>
            {note && <span className="ml-auto font-mono text-[9px] uppercase tracking-[0.08em] text-[var(--ink-subtle)]">{note}</span>}
          </Link>
        );
      })}
    </nav>
  );
}

function UserHeader() {
  const router = useRouter();
  const { data, isLoading } = useDashboardSnapshot();
  const profile = data?.profile;
  const name = profile?.name?.trim();
  const subscription = profile?.subscriptionStatus?.trim();
  const broker = profile?.connectedBroker?.trim();

  async function signOut() {
    await logout();
    router.replace("/login");
  }

  const compactSkeleton = <span className="block h-3 w-16 animate-pulse rounded bg-[var(--line)]" />;
  return (
    <header className="flex min-h-[73px] items-center justify-between gap-4 border-b border-[var(--line)] bg-[var(--canvas)] px-4 sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3 lg:hidden">
        <Button size="icon" variant="quiet" onClick={useDashboardUiStore.getState().openNavigation} aria-label="Open navigation"><Menu size={19} /></Button>
        <span className="font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--ink-subtle)]">CLIENT PORTAL</span>
      </div>
      <div className="ml-auto flex min-w-0 items-center gap-2 sm:gap-3">
        <div className="hidden items-center gap-4 border-r border-[var(--line)] pr-4 sm:flex">
          <HeaderDatum label="Subscription" value={subscription} loading={isLoading} />
          <HeaderDatum label="Broker" value={broker} loading={isLoading} />
        </div>
        <ThemeToggle />
        <details className="group relative">
          <summary className="flex h-9 cursor-pointer list-none items-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-2.5 text-[13px] text-[var(--ink)] outline-none transition hover:border-[var(--line-strong)] focus-visible:ring-2 focus-visible:ring-[var(--focus)] [&::-webkit-details-marker]:hidden">
            <span className="grid h-5 w-5 place-items-center rounded-md bg-[var(--accent-soft)] text-[10px] font-semibold text-[var(--accent)]">{name?.slice(0, 1).toUpperCase() || "?"}</span>
            <span className="hidden max-w-32 truncate font-medium sm:inline">{isLoading ? "Loading" : name || "Profile unavailable"}</span>
            <ChevronDown size={14} className="text-[var(--ink-subtle)] transition group-open:rotate-180" />
          </summary>
          <div role="menu" className="absolute right-0 z-30 mt-2 w-48 rounded-lg border border-[var(--line)] bg-[var(--panel)] p-1.5 shadow-[0_12px_32px_color-mix(in_srgb,var(--ink)_10%,transparent)]">
            <p className="px-2.5 py-2 text-[11px] text-[var(--ink-muted)]">{name || "User profile"}</p>
            <div className="my-1 h-px bg-[var(--line)]" />
            <button type="button" role="menuitem" onClick={signOut} className="flex h-9 w-full items-center gap-2 rounded-md px-2.5 text-left text-[13px] text-[var(--danger)] outline-none transition hover:bg-[var(--danger-soft)] focus-visible:ring-2 focus-visible:ring-[var(--focus)]"><LogOut size={15} /> Log out</button>
          </div>
        </details>
      </div>
    </header>
  );
}

function HeaderDatum({ label, value, loading }: { label: string; value?: string; loading: boolean }) {
  return (
    <div className="min-w-0">
      <p className="mb-0.5 font-mono text-[9px] font-medium uppercase tracking-[0.1em] text-[var(--ink-subtle)]">{label}</p>
      {loading ? <span className="block h-3 w-16 animate-pulse rounded bg-[var(--line)]" /> : <p className="max-w-28 truncate text-[12px] font-medium text-[var(--ink)]">{value || "Unavailable"}</p>}
    </div>
  );
}

export function DashboardShell({ children }: { children: ReactNode }) {
  const isNavigationOpen = useDashboardUiStore((state) => state.isNavigationOpen);
  const closeNavigation = useDashboardUiStore((state) => state.closeNavigation);
  const reducedMotion = useReducedMotion();
  const sidebar = (
    <>
      <div className="flex h-[73px] items-center border-b border-[var(--line)] px-5"><BrandMark /></div>
      <NavContent onNavigate={closeNavigation} />
      <div className="mx-3 mb-4 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] p-3">
        <div className="mb-2 flex items-center gap-2 text-[var(--ink-muted)]"><BarChart3 size={14} /><span className="font-mono text-[10px] tracking-[0.1em]">CENTRAL EXECUTION</span></div>
        <p className="text-[11px] leading-4 text-[var(--ink-muted)]">Strategy files are restricted to the administrator workspace.</p>
      </div>
    </>
  );

  return (
    <div className="min-h-dvh bg-[var(--canvas)] lg:grid lg:grid-cols-[236px_minmax(0,1fr)]">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[236px] flex-col border-r border-[var(--line)] bg-[var(--side-panel)] lg:flex">{sidebar}</aside>
      <AnimatePresence>
        {isNavigationOpen && (
          <motion.div initial={reducedMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 bg-[#071015]/35 lg:hidden">
            <motion.aside initial={reducedMotion ? false : { x: -24 }} animate={{ x: 0 }} exit={{ x: -24 }} transition={{ duration: 0.16 }} className="flex h-full w-[min(290px,84vw)] flex-col border-r border-[var(--line)] bg-[var(--side-panel)] shadow-2xl">{sidebar}</motion.aside>
            <button type="button" aria-label="Close navigation" className="absolute inset-y-0 left-[min(290px,84vw)] right-0" onClick={closeNavigation} />
          </motion.div>
        )}
      </AnimatePresence>
      <div className="min-w-0 lg:col-start-2">
        <UserHeader />
        <MarketTicker />
        <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
