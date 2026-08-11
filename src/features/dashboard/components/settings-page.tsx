"use client";

import { useEffect, useState } from "react";
import { Palette, ShieldCheck, KeyRound, CheckCircle2, AlertCircle } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { DataError } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { useDashboardSnapshot } from "@/features/dashboard/hooks/use-dashboard-data";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";
import { getAccessToken } from "@/lib/session-storage";

export function SettingsPage() {
  const { data, isLoading, isError } = useDashboardSnapshot();

  // 2FA state
  const [totpSetup, setTotpSetup] = useState<{ secret: string; qr_code: string; enabled: boolean } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [twoFaMessage, setTwoFaMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

  useEffect(() => {
    fetch2FASetup();
  }, []);

  async function fetch2FASetup() {
    try {
      const token = getAccessToken();
      const res = await fetch(`${apiBaseUrl}/api/v1/client/auth/2fa/setup`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const json = await res.json();
        setTotpSetup(json);
      }
    } catch {
      // ignore
    }
  }

  async function handleToggle2FA(enable: boolean) {
    if (totpCode.trim().length !== 6) {
      setTwoFaMessage({ type: "error", text: "Please enter a valid 6-digit code from Google Authenticator." });
      return;
    }
    setIsSubmitting(true);
    setTwoFaMessage(null);
    try {
      const token = getAccessToken();
      const endpoint = enable ? "/api/v1/client/auth/2fa/enable" : "/api/v1/client/auth/2fa/disable";
      const res = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ totp_code: totpCode.trim() })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Action failed.");
      }
      setTwoFaMessage({ type: "success", text: data.message });
      setTotpCode("");
      fetch2FASetup();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error updating 2FA";
      setTwoFaMessage({ type: "error", text: msg });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <WorkspacePageTitle eyebrow="SETTINGS" title="Workspace settings">
        Manage appearance, security authenticators, and view account controls.
      </WorkspacePageTitle>
      {isError && <div className="mb-4"><DataError message="Account settings are unavailable." /></div>}
      
      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard>
          <SectionCardHeader eyebrow="APPEARANCE" title="Theme" />
          <div className="flex items-center justify-between gap-4 p-5">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[var(--accent)]">
                <Palette size={16} />
                <span className="font-mono text-[10px] tracking-[0.11em]">DISPLAY</span>
              </div>
              <p className="text-[12px] leading-5 text-[var(--ink-muted)]">Choose a theme that suits your workspace.</p>
            </div>
            <ThemeToggle />
          </div>
        </SectionCard>

        <SectionCard>
          <SectionCardHeader eyebrow="ACCOUNT CONTROLS" title="Trading preferences" />
          <div className="grid divide-y divide-[var(--line)] sm:grid-cols-2 sm:divide-x sm:divide-y-0">
            <ReadOnlyValue label="Lot size" value={data?.preferences?.lotSize} loading={isLoading} />
            <ReadOnlyValue label="Risk settings" value={data?.preferences?.riskSettings} loading={isLoading} />
          </div>
        </SectionCard>
      </div>

      {/* 2FA Security Section */}
      <div className="mt-4">
        <SectionCard>
          <SectionCardHeader eyebrow="SECURITY" title="Google Authenticator (2FA)" />
          <div className="p-5">
            {totpSetup ? (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${totpSetup.enabled ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40" : "bg-amber-50 text-amber-600 dark:bg-amber-950/40"}`}>
                      <KeyRound className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-[var(--ink)]">
                        {totpSetup.enabled ? "Two-Factor Authentication is ENABLED" : "Two-Factor Authentication is DISABLED"}
                      </h4>
                      <p className="text-xs text-[var(--ink-muted)]">
                        {totpSetup.enabled 
                          ? "Your account is secured with Google Authenticator."
                          : "Protect your account with Time-based One-Time Passwords (TOTP)."}
                      </p>
                    </div>
                  </div>
                </div>

                {twoFaMessage && (
                  <div className={`flex items-center gap-2 rounded-lg p-3 text-xs ${twoFaMessage.type === "success" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300" : "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300"}`}>
                    {twoFaMessage.type === "success" ? <CheckCircle2 className="h-4 w-4 shrink-0" /> : <AlertCircle className="h-4 w-4 shrink-0" />}
                    <span>{twoFaMessage.text}</span>
                  </div>
                )}

                {!totpSetup.enabled ? (
                  <div className="grid gap-6 md:grid-cols-[160px_1fr]">
                    <div className="flex flex-col items-center rounded-xl border border-[var(--line)] bg-[var(--panel-raised)] p-3">
                      <img src={totpSetup.qr_code} alt="2FA QR Code" className="h-36 w-36 rounded-lg" />
                    </div>
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs font-semibold text-[var(--ink)]">Step 1: Scan QR Code</p>
                        <p className="text-xs text-[var(--ink-muted)]">Scan this QR code using Google Authenticator or any TOTP app.</p>
                        <div className="mt-2 rounded-md bg-[var(--panel-raised)] p-2 font-mono text-[11px] text-[var(--ink-subtle)]">
                          Secret: <span className="font-bold text-[var(--ink)]">{totpSetup.secret}</span>
                        </div>
                      </div>

                      <div>
                        <p className="text-xs font-semibold text-[var(--ink)]">Step 2: Enter 6-digit Code</p>
                        <div className="mt-2 flex max-w-xs gap-2">
                          <input
                            type="text"
                            maxLength={6}
                            placeholder="000000"
                            value={totpCode}
                            onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                            className="w-full rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3 py-1.5 text-center font-mono text-sm tracking-widest text-[var(--ink)] focus:outline-none"
                          />
                          <button
                            type="button"
                            onClick={() => handleToggle2FA(true)}
                            disabled={isSubmitting || totpCode.length !== 6}
                            className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white transition-all hover:bg-blue-700 disabled:opacity-50"
                          >
                            Enable
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-[var(--line)] bg-[var(--panel-raised)] p-4">
                    <p className="text-xs font-semibold text-[var(--ink)] mb-2">Disable Google Authenticator</p>
                    <p className="text-xs text-[var(--ink-muted)] mb-3">To disable 2FA, enter your current 6-digit code from the authenticator app.</p>
                    <div className="flex max-w-xs gap-2">
                      <input
                        type="text"
                        maxLength={6}
                        placeholder="000000"
                        value={totpCode}
                        onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                        className="w-full rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3 py-1.5 text-center font-mono text-sm tracking-widest text-[var(--ink)] focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => handleToggle2FA(false)}
                        disabled={isSubmitting || totpCode.length !== 6}
                        className="rounded-lg bg-red-600 px-4 py-1.5 text-xs font-semibold text-white transition-all hover:bg-red-700 disabled:opacity-50"
                      >
                        Disable
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-[var(--ink-muted)]">Loading security settings...</p>
            )}
          </div>
        </SectionCard>
      </div>

      <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] px-4 py-3.5 text-[12px] leading-5 text-[var(--ink-muted)]">
        <ShieldCheck size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" /> 
        <span>Strategy configuration and Python files are controlled by the administrator. This view does not permit strategy edits.</span>
      </div>
    </div>
  );
}

function ReadOnlyValue({ label, value, loading }: { label: string; value?: string | null; loading: boolean }) {
  return (
    <div className="px-5 py-4">
      <p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.11em] text-[var(--ink-subtle)]">{label}</p>
      {loading ? <span className="block h-5 w-28 animate-pulse rounded bg-[var(--line)]" /> : <p className="text-[14px] font-medium text-[var(--ink)]">{value || "Unavailable"}</p>}
      <p className="mt-1.5 text-[11px] leading-4 text-[var(--ink-muted)]">Read from the approved account configuration.</p>
    </div>
  );
}