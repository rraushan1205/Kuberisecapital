"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, ArrowRight, CheckCircle2, MailCheck } from "lucide-react";
import { AuthHeading, FieldBlock, PasswordField, SubmitLabel } from "@/components/auth-primitives";

const emailSchema = z.object({ email: z.string().trim().email("Enter a valid email address.") });
const passwordSchema = z.object({
  password: z.string().min(12, "Use at least 12 characters."),
  confirmPassword: z.string().min(1, "Confirm your new password."),
}).refine((values) => values.password === values.confirmPassword, { path: ["confirmPassword"], message: "Passwords do not match." });

export function ForgotPasswordForm() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const form = useForm<z.infer<typeof emailSchema>>({ resolver: zodResolver(emailSchema), mode: "onBlur", defaultValues: { email: "" } });
  const { errors, isSubmitting } = form.formState;
  async function onSubmit(values: z.infer<typeof emailSchema>) {
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    setSentTo(values.email);
  }
  if (sentTo) return <PasswordEmailSent email={sentTo} onUseDifferent={() => { setSentTo(null); form.reset(); }} />;
  return (
    <>
      <AuthHeading eyebrow="ACCOUNT RECOVERY" title="Reset your password.">
        Enter the email associated with your account. We’ll send a secure reset link if it exists.
      </AuthHeading>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-5">
        <FieldBlock label="Email address" htmlFor="email" error={errors.email?.message}>
          <input id="email" autoComplete="email" inputMode="email" placeholder="you@firm.com" className="auth-input" aria-invalid={!!errors.email} {...form.register("email")} />
        </FieldBlock>
        <button type="submit" className="primary-button" disabled={isSubmitting}><SubmitLabel loading={isSubmitting}>Send reset link <ArrowRight size={16} /></SubmitLabel></button>
      </form>
      <Link href="/login" className="mt-7 inline-flex items-center gap-2 text-link text-[13px]"><ArrowLeft size={15} /> Back to sign in</Link>
    </>
  );
}

function PasswordEmailSent({ email, onUseDifferent }: { email: string; onUseDifferent: () => void }) {
  return (
    <div>
      <div className="mb-7 grid h-12 w-12 place-items-center rounded-xl bg-[var(--positive-soft)] text-[var(--positive)]"><MailCheck size={23} /></div>
      <AuthHeading eyebrow="CHECK YOUR INBOX" title="Reset link sent.">
        If <strong className="font-medium text-[var(--ink)]">{email}</strong> matches an account, a reset link is on its way. It expires in 30 minutes.
      </AuthHeading>
      <div className="space-y-3">
        <Link href="/login" className="primary-button">Return to sign in</Link>
        <button type="button" onClick={onUseDifferent} className="secondary-button w-full">Use a different email</button>
      </div>
    </div>
  );
}

export function ResetPasswordForm() {
  const params = useSearchParams();
  const [complete, setComplete] = useState(false);
  const form = useForm<z.infer<typeof passwordSchema>>({ resolver: zodResolver(passwordSchema), mode: "onBlur", defaultValues: { password: "", confirmPassword: "" } });
  const { errors, isSubmitting } = form.formState;
  const isMissingToken = !params.get("token");
  async function onSubmit() {
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    setComplete(true);
  }
  if (isMissingToken) return <ResetLinkProblem />;
  if (complete) return <PasswordChanged />;
  return (
    <>
      <AuthHeading eyebrow="ACCOUNT RECOVERY" title="Choose a new password.">
        Use a long, unique password you do not use for other services.
      </AuthHeading>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-5">
        <FieldBlock label="New password" htmlFor="password" error={errors.password?.message} hint="12+ characters">
          <PasswordField id="password" autoComplete="new-password" placeholder="Create new password" error={!!errors.password} {...form.register("password")} />
        </FieldBlock>
        <FieldBlock label="Confirm new password" htmlFor="confirmPassword" error={errors.confirmPassword?.message}>
          <PasswordField id="confirmPassword" autoComplete="new-password" placeholder="Repeat new password" error={!!errors.confirmPassword} {...form.register("confirmPassword")} />
        </FieldBlock>
        <button type="submit" className="primary-button" disabled={isSubmitting}><SubmitLabel loading={isSubmitting}>Save new password <ArrowRight size={16} /></SubmitLabel></button>
      </form>
    </>
  );
}

function PasswordChanged() {
  return <div><div className="mb-7 grid h-12 w-12 place-items-center rounded-xl bg-[var(--positive-soft)] text-[var(--positive)]"><CheckCircle2 size={24} /></div><AuthHeading eyebrow="PASSWORD UPDATED" title="You’re all set.">Your password has been changed. Sign in using your new credentials.</AuthHeading><Link href="/login" className="primary-button">Continue to sign in <ArrowRight size={16} /></Link></div>;
}

function ResetLinkProblem() {
  return <div><div className="mb-7 grid h-12 w-12 place-items-center rounded-xl bg-[var(--warning-soft)] text-[var(--warning)]"><MailCheck size={23} /></div><AuthHeading eyebrow="LINK REQUIRED" title="This reset link is incomplete.">Request a new password reset link to continue. For security, reset links can only be used once.</AuthHeading><Link href="/forgot-password" className="primary-button">Request another link <ArrowRight size={16} /></Link></div>;
}
