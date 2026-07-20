"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthHeading, FieldBlock, PasswordField, SubmitLabel } from "@/components/auth-primitives";
import { AdminApiError, adminApi } from "@/features/admin/api/admin-api";

const schema = z.object({ email: z.string().trim().email("Enter a valid administrator email."), password: z.string().min(1, "Enter your password.") });
type LoginValues = z.infer<typeof schema>;

export function AdminLoginForm() {
  const router = useRouter();
  const form = useForm<LoginValues>({ resolver: zodResolver(schema), mode: "onBlur", defaultValues: { email: "", password: "" } });
  const { errors, isSubmitting } = form.formState;
  async function onSubmit(values: LoginValues) {
    try { await adminApi.login(values.email, values.password); router.replace("/admin/dashboard"); }
    catch (error) { form.setError("root", { message: error instanceof AdminApiError ? error.message : "Admin sign-in could not be completed." }); }
  }
  return <><AuthHeading eyebrow="RESTRICTED ACCESS" title="Admin sign in.">This workspace is limited to the designated Super Admin account.</AuthHeading><form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-5"><FieldBlock label="Administrator email" htmlFor="admin-email" error={errors.email?.message}><input id="admin-email" autoComplete="username" inputMode="email" placeholder="admin@company.com" className="auth-input" aria-invalid={!!errors.email} {...form.register("email")} /></FieldBlock><FieldBlock label="Password" htmlFor="admin-password" error={errors.password?.message}><PasswordField id="admin-password" autoComplete="current-password" placeholder="Enter your password" error={!!errors.password} {...form.register("password")} /></FieldBlock>{errors.root?.message && <p role="alert" className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2.5 text-xs leading-5 text-[var(--danger)]">{errors.root.message}</p>}<button type="submit" className="primary-button" disabled={isSubmitting}><SubmitLabel loading={isSubmitting}>Continue to Admin Portal <ArrowRight size={16} /></SubmitLabel></button></form><div className="mt-7 border-t border-[var(--line)] pt-5"><div className="flex items-start gap-2.5 text-[12px] leading-5 text-[var(--ink-muted)]"><ShieldCheck size={16} className="mt-0.5 shrink-0 text-[var(--danger)]" /><span>Super Admin authorization is verified again by every protected backend endpoint.</span></div></div></>;
}
