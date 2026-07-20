import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth-shell";
import { EmailVerificationSuccess } from "@/components/account-status";

export const metadata: Metadata = { title: "Email confirmed" };

export default function EmailVerificationSuccessPage() {
  return <AuthShell mode="status"><Suspense><EmailVerificationSuccess /></Suspense></AuthShell>;
}
