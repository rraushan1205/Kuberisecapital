"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { AuthHeading, FieldBlock, PasswordField, SubmitLabel } from "@/components/auth-primitives";
import { login } from "@/lib/auth-client";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
  remember: z.boolean().optional(),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const nextPath = params.get("next") || "/dashboard";
  const [loginError, setLoginError] = useState<string | null>(null);
  const form = useForm<LoginValues>({ 
    resolver: zodResolver(loginSchema), 
    mode: "onBlur", 
    defaultValues: { email: "", password: "", remember: false } 
  });

  async function onSubmit(values: LoginValues) {
    setLoginError(null);
    
    try {
      const status = await login(values.email, values.password);
      if (status === "pending") {
        router.replace(`/pending-approval?email=${encodeURIComponent(values.email)}`);
        return;
      }
      if (status === "rejected") {
        router.replace(`/account-rejected?email=${encodeURIComponent(values.email)}`);
        return;
      }
      router.push(nextPath);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Sign in failed.";
      setLoginError(errorMessage);
      form.setError("password", { message: errorMessage });
    }
  }

  const { errors, isSubmitting } = form.formState;
  return (
    <>
      <AuthHeading eyebrow="MEMBER SIGN IN" title="Welcome back.">
        Sign in to continue to your execution workspace.
      </AuthHeading>
      {loginError && (
        <div className="rounded-lg border border-[var(--danger)] bg-[var(--danger)]/5 px-4 py-3 text-sm text-[var(--danger)]">
          {loginError}
        </div>
      )}
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-5">
        <FieldBlock label="Email address" htmlFor="email" error={errors.email?.message}>
          <input id="email" autoComplete="email" inputMode="email" placeholder="you@firm.com" className="auth-input" aria-invalid={!!errors.email} {...form.register("email")} />
        </FieldBlock>
        <FieldBlock label="Password" htmlFor="password" error={errors.password?.message}>
          <PasswordField id="password" autoComplete="current-password" placeholder="Enter your password" error={!!errors.password} {...form.register("password")} />
        </FieldBlock>
        <div className="flex items-center justify-between gap-4 pt-0.5">
          <label className="flex cursor-pointer items-center gap-2 text-[13px] text-[var(--ink-muted)]">
            <input type="checkbox" className="h-3.5 w-3.5 rounded border-[var(--line-strong)] accent-[var(--accent)]" {...form.register("remember")} />
            Keep this device signed in
          </label>
          <Link href="/forgot-password" className="text-link text-[13px]">Forgot password?</Link>
        </div>
        <button type="submit" className="primary-button mt-1" disabled={isSubmitting}>
          <SubmitLabel loading={isSubmitting}>Continue <ArrowRight size={16} /></SubmitLabel>
        </button>
      </form>
      <div className="mt-7 border-t border-[var(--line)] pt-5">
        <div className="flex items-start gap-2.5 text-[12px] leading-5 text-[var(--ink-muted)]"><ShieldCheck size={16} className="mt-0.5 shrink-0 text-[var(--positive)]" /> <span>Access is restricted to approved members. New to Stratum? <Link href="/register" className="text-link">Request access</Link>.</span></div>
      </div>
    </>
  );
}
