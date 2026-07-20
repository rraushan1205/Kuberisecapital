import type { Metadata } from "next";
import { UsersPage } from "@/features/admin/components/users-page";

export const metadata: Metadata = { title: "User management" };

export default function AdminUsersRoute() {
  return <UsersPage />;
}
