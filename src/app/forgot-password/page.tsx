import type { Metadata } from "next";
import { AuthShell } from "@/components/auth-shell";
import { ForgotPasswordForm } from "@/components/password-flows";

export const metadata: Metadata = { title: "Reset password" };

export default function ForgotPasswordPage() {
  return <AuthShell><ForgotPasswordForm /></AuthShell>;
}
