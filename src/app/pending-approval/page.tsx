import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth-shell";
import { PendingApproval } from "@/components/account-status";

export const metadata: Metadata = { title: "Approval pending" };

export default function PendingApprovalPage() {
  return <AuthShell mode="status"><Suspense><PendingApproval /></Suspense></AuthShell>;
}
