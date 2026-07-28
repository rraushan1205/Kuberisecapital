import type { Metadata } from "next";
import { DashboardOverviewEnhanced } from "@/features/dashboard/components/dashboard-overview-enhanced";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return <DashboardOverviewEnhanced />;
}
