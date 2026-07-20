import type { Metadata } from "next";
import { AdminDashboardPage } from "@/features/admin/components/admin-dashboard-page";

export const metadata: Metadata = { title: "Administration" };

export default function AdminDashboardRoute() {
  return <AdminDashboardPage />;
}
