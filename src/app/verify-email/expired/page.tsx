import type { Metadata } from "next";
import { AuthShell } from "@/components/auth-shell";
import { EmailVerificationExpired } from "@/components/account-status";

export const metadata: Metadata = { title: "Verification expired" };

export default function EmailVerificationExpiredPage() {
  return <AuthShell mode="status"><EmailVerificationExpired /></AuthShell>;
}
