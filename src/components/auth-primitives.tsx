"use client";

import { Eye, EyeOff, LoaderCircle } from "lucide-react";
import type { InputHTMLAttributes, ReactNode } from "react";
import { useState } from "react";

export function AuthHeading({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <div className="mb-8">
      {eyebrow && <p className="mb-3 font-mono text-[11px] font-medium tracking-[0.13em] text-[var(--accent)]">{eyebrow}</p>}
      <h2 className="text-[32px] font-semibold leading-[1.05] tracking-[-0.055em] text-[var(--ink)] sm:text-[36px]">{title}</h2>
      {children && <div className="mt-3 text-[14px] leading-6 text-[var(--ink-muted)]">{children}</div>}
    </div>
  );
}

export function FieldBlock({ label, htmlFor, error, hint, children }: { label: string; htmlFor: string; error?: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <label htmlFor={htmlFor} className="text-[13px] font-medium text-[var(--ink)]">{label}</label>
        {hint && <span className="text-[11px] text-[var(--ink-subtle)]">{hint}</span>}
      </div>
      {children}
      {error && <p role="alert" className="mt-1.5 text-xs leading-4 text-[var(--danger)]">{error}</p>}
    </div>
  );
}

type PasswordFieldProps = InputHTMLAttributes<HTMLInputElement> & { error?: boolean };

export function PasswordField({ error, className = "", ...props }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input {...props} type={visible ? "text" : "password"} className={`auth-input pr-11 ${className}`} aria-invalid={error || undefined} />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-[var(--ink-subtle)] outline-none transition hover:text-[var(--ink)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus)]"
        aria-label={visible ? "Hide password" : "Show password"}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

export function SubmitLabel({ loading, children }: { loading: boolean; children: ReactNode }) {
  return loading ? <><LoaderCircle size={16} className="animate-spin" /> Processing</> : <>{children}</>;
}

export function DividerLabel({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="h-px flex-1 bg-[var(--line)]" />
      <span className="font-mono text-[10px] tracking-[0.1em] text-[var(--ink-subtle)]">{children}</span>
      <span className="h-px flex-1 bg-[var(--line)]" />
    </div>
  );
}
