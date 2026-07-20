import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth-shell";
import { ResetPasswordForm } from "@/components/password-flows";

export const metadata: Metadata = { title: "Choose a new password" };

export default function ResetPasswordPage() {
  return <AuthShell><Suspense><ResetPasswordForm /></Suspense></AuthShell>;
}
