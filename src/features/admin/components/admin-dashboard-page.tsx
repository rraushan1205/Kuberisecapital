"use client";

import { ArrowRight, Bell, ClipboardList, FileCode2, Users, UserRoundCheck, UserRoundPlus } from "lucide-react";
import Link from "next/link";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";

const modules = [
  { href: "/admin/users", title: "User management", body: "Review registered account records.", icon: Users },
  { href: "/admin/pending-registrations", title: "Pending registrations", body: "Review registrations awaiting account action.", icon: UserRoundPlus },
  { href: "/admin/subscriptions", title: "Subscription approval", body: "Activate eligible user subscriptions.", icon: UserRoundCheck },
  { href: "/admin/strategies", title: "Strategies", body: "Upload and control approved strategy files.", icon: FileCode2 },
  { href: "/admin/logs", title: "Execution logs", body: "Review logged execution commands.", icon: ClipboardList },
  { href: "/admin/announcements", title: "Announcements", body: "Create and review administrative announcements.", icon: Bell },
];

export function AdminDashboardPage() {
  return <div><AdminPageTitle eyebrow="SUPER ADMIN" title="Administration workspace">Select an operational module. This dashboard does not generate synthetic activity or analytics.</AdminPageTitle><SectionCard><SectionCardHeader eyebrow="ADMIN MODULES" title="Operational controls" /><div className="grid divide-y divide-[var(--line)] md:grid-cols-2 md:divide-x md:divide-y-0 xl:grid-cols-3">{modules.map(({ href, title, body, icon: Icon }) => <Link key={href} href={href} className="group block px-5 py-5 outline-none transition hover:bg-[var(--panel-raised)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus)]"><div className="mb-6 text-[var(--danger)]"><Icon size={18} /></div><h2 className="text-[13px] font-semibold text-[var(--ink)]">{title}</h2><p className="mt-1.5 text-[12px] leading-5 text-[var(--ink-muted)]">{body}</p><span className="mt-4 inline-flex items-center gap-1.5 text-[11px] font-medium text-[var(--danger)]">Open module <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" /></span></Link>)}</div></SectionCard></div>;
}
