import type { Metadata } from "next";
import { AdminLoginForm } from "@/features/admin/components/admin-login-form";
import { AdminLoginShell } from "@/features/admin/components/admin-login-shell";

export const metadata: Metadata = { title: "Admin sign in" };

export default function AdminLoginPage() {
  return <AdminLoginShell><AdminLoginForm /></AdminLoginShell>;
}
