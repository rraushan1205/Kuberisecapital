"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, ShieldCheck, KeyRound, Lock, Sparkles } from "lucide-react";
import { AuthHeading, FieldBlock, PasswordField, SubmitLabel } from "@/components/auth-primitives";
import { login, verify2FALogin, refreshClientSession } from "@/lib/auth-client";

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

  // 2FA state
  const [step2FA, setStep2FA] = useState(false);
  const [temp2faToken, setTemp2faToken] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [totpSubmitting, setTotpSubmitting] = useState(false);

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
      const res = await login(values.email, values.password);
      if (res.requires2FA && res.temp2faToken) {
        setTemp2faToken(res.temp2faToken);
        setStep2FA(true);
        return;
      }

      if (res.status === "PENDING") {
        router.replace(`/pending-approval?email=${encodeURIComponent(values.email)}`);
        return;
      }
      if (res.status === "REJECTED") {
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

  async function handleVerify2FA(e: React.FormEvent) {
    e.preventDefault();
    if (!temp2faToken || totpCode.trim().length !== 6) {
      setLoginError("Please enter a valid 6-digit Google Authenticator code.");
      return;
    }

    setLoginError(null);
    setTotpSubmitting(true);

    try {
      const status = await verify2FALogin(temp2faToken, totpCode.trim());
      if (status === "PENDING") {
        router.replace(`/pending-approval`);
        return;
      }
      if (status === "REJECTED") {
        router.replace(`/account-rejected`);
        return;
      }
      router.push(nextPath);
    } catch (error) {
      setTotpSubmitting(false);
      const errorMessage = error instanceof Error ? error.message : "Invalid code.";
      setLoginError(errorMessage);
    }
  }

  async function handleFyersLogin() {
    setLoginError(null);
    setFyersLoading(true);

    try {
      const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
      const response = await fetch(`${apiBaseUrl}/api/v1/client/auth/oauth/fyers/login`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        throw new Error("Failed to initiate Fyers login");
      }

      const data = await response.json();
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
    <div className="mx-auto w-full max-w-[420px] rounded-2xl border border-slate-200/80 bg-white p-8 shadow-xl shadow-slate-100 dark:border-slate-800 dark:bg-slate-900 dark:shadow-none">
      {step2FA ? (
        <div>
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
              <KeyRound className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Two-Factor Authentication
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Enter the 6-digit verification code from your Google Authenticator app.
            </p>
          </div>

          {loginError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-600 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
              {loginError}
            </div>
          )}

          <form onSubmit={handleVerify2FA} className="space-y-5">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Authenticator Code
              </label>
              <input
                type="text"
                maxLength={6}
                placeholder="000000"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-center text-2xl font-mono tracking-widest text-slate-900 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:focus:border-blue-400"
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={totpSubmitting || totpCode.length !== 6}
              className="w-full rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white transition-all hover:bg-blue-700 disabled:opacity-50"
            >
              {totpSubmitting ? "Verifying..." : "Verify & Continue"}
            </button>

            <button
              type="button"
              onClick={() => { setStep2FA(false); setLoginError(null); }}
              className="w-full text-center text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              ← Back to Sign In
            </button>
          </form>
        </div>
      ) : (
        <>
          <div className="mb-6 text-center">
            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Welcome back
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Sign in to your Kuberise workspace
            </p>
          </div>

          {loginError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-600 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
              {loginError}
            </div>
          )}

          <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 transition-all focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                {...form.register("email")}
              />
              {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label htmlFor="password" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Password
                </label>
                <Link href="/forgot-password" className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
                  Forgot?
                </Link>
              </div>
              <PasswordField
                id="password"
                autoComplete="current-password"
                placeholder="••••••••"
                error={!!errors.password}
                {...form.register("password")}
              />
              {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-slate-800 disabled:opacity-50 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
            >
              {isSubmitting ? "Signing in..." : "Continue"}
              <ArrowRight size={16} />
            </button>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-800" />
            </div>
            <div className="relative flex justify-center text-xs tracking-wider uppercase">
              <span className="bg-white px-2 text-slate-400 dark:bg-slate-900">or continue with</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleFyersLogin}
            disabled={fyersLoading}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-2.5 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300"
          >
            <ShieldCheck className="h-4 w-4 text-blue-600" />
            {fyersLoading ? "Initiating Fyers Login..." : "Sign in with Fyers Broker"}
          </button>
        </>
      )}
    </div>
  );
}