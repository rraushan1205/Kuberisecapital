"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { AuthHeading, FieldBlock, PasswordField, SubmitLabel } from "@/components/auth-primitives";
import { login, refreshClientSession } from "@/lib/auth-client";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const nextPath = params.get("next") || "/dashboard";
  const [loginError, setLoginError] = useState<string | null>(null);
  const [fyersLoading, setFyersLoading] = useState(false);
  const form = useForm<LoginValues>({ 
    resolver: zodResolver(loginSchema), 
    mode: "onBlur", 
    defaultValues: { email: "", password: "" }
  });

  useEffect(() => {
    let active = true;
    refreshClientSession()
      .then(() => { if (active) router.replace(nextPath); })
      .catch(() => undefined);
    return () => { active = false; };
  }, [nextPath, router]);

  async function onSubmit(values: LoginValues) {
    setLoginError(null);
    
    try {
      const status = await login(values.email, values.password);
      if (status === "PENDING") {
        router.replace(`/pending-approval?email=${encodeURIComponent(values.email)}`);
        return;
      }
      if (status === "REJECTED") {
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

  async function handleFyersLogin() {
    setLoginError(null);
    setFyersLoading(true);

    try {
      // Use same API base URL pattern as rest of the app
      const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
      
      // Call backend OAuth login endpoint
      const response = await fetch(`${apiBaseUrl}/api/v1/client/auth/oauth/fyers/login`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        throw new Error("Failed to initiate Fyers login");
      }

      const data = await response.json();
      
      // Redirect to Fyers OAuth page
      if (data.authorize_url) {
        window.location.href = data.authorize_url;
      } else {
        throw new Error("No authorization URL received");
      }
    } catch (error) {
      setFyersLoading(false);
      const errorMessage = error instanceof Error ? error.message : "Unable to authenticate with Fyers.";
      setLoginError(errorMessage);
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
        <div className="flex items-center justify-end pt-0.5">
          <Link href="/forgot-password" className="text-link text-[13px]">Forgot password?</Link>
        </div>
        <button type="submit" className="primary-button mt-1" disabled={isSubmitting}>
          <SubmitLabel loading={isSubmitting}>Continue <ArrowRight size={16} /></SubmitLabel>
        </button>
      </form>
      
      <div className="mt-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-[var(--line)]"></div>
        <span className="text-xs text-[var(--ink-muted)]">or</span>
        <div className="h-px flex-1 bg-[var(--line)]"></div>
      </div>

      <button
        type="button"
        onClick={handleFyersLogin}
        disabled={isSubmitting || fyersLoading}
        className="mt-6 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-[var(--line)] bg-[var(--canvas)] text-[var(--ink)] hover:bg-[var(--canvas-contrast)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {fyersLoading ? (
          <span className="text-sm">Redirecting to Fyers...</span>
        ) : (
          <span className="text-sm font-medium">Continue with Fyers</span>
        )}
      </button>

      <div className="mt-7 border-t border-[var(--line)] pt-5">
        <div className="flex items-start gap-2.5 text-[12px] leading-5 text-[var(--ink-muted)]"><ShieldCheck size={16} className="mt-0.5 shrink-0 text-[var(--positive)]" /> <span>Access is restricted to approved members. New to Stratum? <Link href="/register" className="text-link">Request access</Link>.</span></div>
      </div>
    </>
  );
}
