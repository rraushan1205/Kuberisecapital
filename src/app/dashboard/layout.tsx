import { SessionGuard } from "@/components/session-guard";
import { DashboardShell } from "@/features/dashboard/components/dashboard-shell";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionGuard kind="user">
      <DashboardShell>{children}</DashboardShell>
    </SessionGuard>
  );
}
