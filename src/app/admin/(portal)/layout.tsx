import { AdminShell } from "@/features/admin/components/admin-shell";

export default function AdminPortalLayout({ children }: { children: React.ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
