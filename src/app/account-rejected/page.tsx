import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth-shell";
import { AccountRejected } from "@/components/account-status";

export const metadata: Metadata = { title: "Account not approved" };

export default function AccountRejectedPage() {
  return <AuthShell mode="status"><Suspense><AccountRejected /></Suspense></AuthShell>;
}
