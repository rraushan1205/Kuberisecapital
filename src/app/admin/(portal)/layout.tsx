import { SessionGuard } from "@/components/session-guard";
import { AdminShell } from "@/features/admin/components/admin-shell";

export default function AdminPortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionGuard kind="admin">
      <AdminShell>{children}</AdminShell>
    </SessionGuard>
  );
}
