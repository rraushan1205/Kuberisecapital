import type { Metadata } from "next";
import { AuthShell } from "@/components/auth-shell";
import { RegisterForm } from "@/components/register-form";

export const metadata: Metadata = { title: "Request access" };

export default function RegisterPage() {
  return <AuthShell mode="enrollment"><RegisterForm /></AuthShell>;
}
