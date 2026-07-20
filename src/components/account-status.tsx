"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowRight, CheckCircle2, CircleX, Clock3, Mail, RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { AuthHeading } from "@/components/auth-primitives";

function StatusIcon({ tone, children }: { tone: "positive" | "warning" | "danger"; children: React.ReactNode }) {
  const colors = {
    positive: "bg-[var(--positive-soft)] text-[var(--positive)]",
    warning: "bg-[var(--warning-soft)] text-[var(--warning)]",
    danger: "bg-[var(--danger-soft)] text-[var(--danger)]",
  };
  return <div className={`mb-7 grid h-12 w-12 place-items-center rounded-xl ${colors[tone]}`}>{children}</div>;
}

function EmailReadout() {
  const email = useSearchParams().get("email");
  return email ? <span className="font-medium text-[var(--ink)]">{email}</span> : null;
}

export function PendingApproval() {
  return (
    <div>
      <StatusIcon tone="warning"><Clock3 size={24} /></StatusIcon>
      <AuthHeading eyebrow="REGISTRATION RECEIVED" title="Your account is under review.">
        Your registration has been received. Your account is awaiting administrator approval before you can access the platform.
      </AuthHeading>
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] p-4">
        <div className="mb-1.5 flex items-center gap-2 text-[12px] font-medium text-[var(--ink)]"><Mail size={14} className="text-[var(--accent)]" /> Status notifications</div>
        <p className="text-[12px] leading-5 text-[var(--ink-muted)]">We’ll notify <EmailReadout /> once the review is complete. Do not submit another application while this request is open.</p>
      </div>
      <div className="mt-5 border-l-2 border-[var(--accent)] pl-3.5 text-[12px] leading-5 text-[var(--ink-muted)]">Approvals are completed by your administrator, not by automated account provisioning.</div>
      <Link href="/login" className="secondary-button mt-7 w-full">Return to sign in</Link>
    </div>
  );
}

export function AccountRejected() {
  return (
    <div>
      <StatusIcon tone="danger"><CircleX size={24} /></StatusIcon>
      <AuthHeading eyebrow="ACCESS NOT APPROVED" title="We can’t activate this account.">
        The registration associated with <EmailReadout /> was not approved for platform access.
      </AuthHeading>
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] p-4 text-[12px] leading-5 text-[var(--ink-muted)]">If you believe this is in error, contact the person or organization that issued your invitation. They can provide the appropriate next step.</div>
      <Link href="/login" className="secondary-button mt-7 w-full"><ArrowLeft size={15} /> Return to sign in</Link>
    </div>
  );
}

export function EmailVerificationSuccess() {
  const email = useSearchParams().get("email");
  const statusHref = email ? `/pending-approval?email=${encodeURIComponent(email)}` : "/pending-approval";
  return (
    <div>
      <StatusIcon tone="positive"><CheckCircle2 size={24} /></StatusIcon>
      <AuthHeading eyebrow="EMAIL CONFIRMED" title="Your email is verified.">
        <EmailReadout /> is confirmed. Your registration is now queued for administrator approval.
      </AuthHeading>
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] p-4 text-[12px] leading-5 text-[var(--ink-muted)]">You’ll receive an update when the review is complete. Platform access remains unavailable until approval.</div>
      <Link href={statusHref} className="primary-button mt-7">View account status <ArrowRight size={16} /></Link>
    </div>
  );
}

export function EmailVerificationExpired() {
  const [sent, setSent] = useState(false);
  return (
    <div>
      <StatusIcon tone="warning"><ShieldAlert size={24} /></StatusIcon>
      <AuthHeading eyebrow="VERIFICATION EXPIRED" title="That link has expired.">
        Verification links are intentionally short-lived. Request a fresh link to finish confirming your email address.
      </AuthHeading>
      {sent ? (
        <div className="rounded-lg border border-[var(--positive)] bg-[var(--positive-soft)] p-4 text-[13px] leading-5 text-[var(--positive)]">A new verification link is on its way. Please check your inbox and spam folder.</div>
      ) : (
        <button type="button" onClick={() => setSent(true)} className="primary-button">Resend verification email <RefreshCw size={16} /></button>
      )}
      <Link href="/login" className="mt-5 inline-flex items-center gap-2 text-link text-[13px]"><ArrowLeft size={15} /> Return to sign in</Link>
    </div>
  );
}
