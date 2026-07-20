"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, BadgeCheck, Check, CircleAlert, LoaderCircle } from "lucide-react";
import { AuthHeading, FieldBlock, PasswordField, SubmitLabel } from "@/components/auth-primitives";

const registerSchema = z.object({
  fullName: z.string().trim().min(2, "Enter your full name.").max(80, "Use 80 characters or fewer."),
  email: z.string().trim().email("Enter a valid email address."),
  phone: z.string().trim().min(7, "Enter a valid phone number.").max(24, "Enter a valid phone number."),
  invitationCode: z.string().trim().min(5, "An invitation code is required."),
  password: z.string().min(12, "Use at least 12 characters."),
  confirmPassword: z.string().min(1, "Confirm your password."),
}).refine((values) => values.password === values.confirmPassword, {
  path: ["confirmPassword"],
  message: "Passwords do not match.",
});

type RegisterValues = z.infer<typeof registerSchema>;
type InviteState = "idle" | "checking" | "valid" | "invalid";

async function validateInvitationCode(code: string): Promise<boolean> {
  await new Promise((resolve) => window.setTimeout(resolve, 450));
  // UI adapter: replace with an authenticated server-side invitation lookup.
  return code.trim().length >= 5 && !code.trim().toLowerCase().includes("invalid");
}

export function RegisterForm() {
  const router = useRouter();
  const [inviteState, setInviteState] = useState<InviteState>("idle");
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    mode: "onBlur",
    defaultValues: { fullName: "", email: "", phone: "", invitationCode: "", password: "", confirmPassword: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function checkInvitation() {
    const code = form.getValues("invitationCode");
    if (!code.trim()) return;
    setInviteState("checking");
    const valid = await validateInvitationCode(code);
    setInviteState(valid ? "valid" : "invalid");
    if (!valid) form.setError("invitationCode", { message: "This invitation code is not active." });
    else form.clearErrors("invitationCode");
  }

  async function onSubmit(values: RegisterValues) {
    let isValid = inviteState === "valid";
    if (!isValid) {
      setInviteState("checking");
      isValid = await validateInvitationCode(values.invitationCode);
      setInviteState(isValid ? "valid" : "invalid");
    }
    if (!isValid) {
      form.setError("invitationCode", { message: "This invitation code is not active." });
      return;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 350));
    router.push(`/verify-email/success?email=${encodeURIComponent(values.email)}`);
  }

  return (
    <>
      <AuthHeading eyebrow="MEMBER ENROLLMENT" title="Request access.">
        An active invitation is required. Your request will be reviewed after email verification.
      </AuthHeading>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-[18px]">
        <FieldBlock label="Full name" htmlFor="fullName" error={errors.fullName?.message}>
          <input id="fullName" autoComplete="name" placeholder="Your full name" className="auth-input" aria-invalid={!!errors.fullName} {...form.register("fullName")} />
        </FieldBlock>
        <div className="grid gap-4 sm:grid-cols-2">
          <FieldBlock label="Work email" htmlFor="email" error={errors.email?.message}>
            <input id="email" autoComplete="email" inputMode="email" placeholder="you@firm.com" className="auth-input" aria-invalid={!!errors.email} {...form.register("email")} />
          </FieldBlock>
          <FieldBlock label="Phone number" htmlFor="phone" error={errors.phone?.message}>
            <input id="phone" autoComplete="tel" inputMode="tel" placeholder="+1 555 012 3456" className="auth-input" aria-invalid={!!errors.phone} {...form.register("phone")} />
          </FieldBlock>
        </div>
        <FieldBlock label="Invitation code" htmlFor="invitationCode" error={errors.invitationCode?.message} hint="Required">
          <div className="relative">
            <input
              id="invitationCode"
              autoComplete="off"
              placeholder="Enter code"
              className="auth-input pr-10 font-mono uppercase tracking-[0.05em]"
              aria-invalid={!!errors.invitationCode || inviteState === "invalid"}
              {...form.register("invitationCode", { onChange: () => setInviteState("idle"), onBlur: () => void checkInvitation() })}
            />
            <span className="absolute inset-y-0 right-3 flex items-center" aria-live="polite">
              {inviteState === "checking" && <LoaderCircle size={16} className="animate-spin text-[var(--ink-subtle)]" />}
              {inviteState === "valid" && <BadgeCheck size={17} className="text-[var(--positive)]" />}
              {inviteState === "invalid" && <CircleAlert size={17} className="text-[var(--danger)]" />}
            </span>
          </div>
          {inviteState === "valid" && <p className="mt-1.5 flex items-center gap-1 text-xs text-[var(--positive)]"><Check size={13} /> Invitation recognized.</p>}
        </FieldBlock>
        <div className="grid gap-4 sm:grid-cols-2">
          <FieldBlock label="Password" htmlFor="password" error={errors.password?.message} hint="12+ characters">
            <PasswordField id="password" autoComplete="new-password" placeholder="Create password" error={!!errors.password} {...form.register("password")} />
          </FieldBlock>
          <FieldBlock label="Confirm password" htmlFor="confirmPassword" error={errors.confirmPassword?.message}>
            <PasswordField id="confirmPassword" autoComplete="new-password" placeholder="Repeat password" error={!!errors.confirmPassword} {...form.register("confirmPassword")} />
          </FieldBlock>
        </div>
        <p className="pt-0.5 text-[11px] leading-4 text-[var(--ink-subtle)]">By submitting, you confirm that the information provided is accurate and that you are authorized to use the invitation.</p>
        <button type="submit" className="primary-button" disabled={isSubmitting || inviteState === "checking"}>
          <SubmitLabel loading={isSubmitting}>Submit request <ArrowRight size={16} /></SubmitLabel>
        </button>
      </form>
      <p className="mt-6 text-center text-[13px] text-[var(--ink-muted)]">Already approved? <Link href="/login" className="text-link">Sign in</Link></p>
    </>
  );
}
