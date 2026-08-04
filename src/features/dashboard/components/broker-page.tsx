"use client";

import { useState } from "react";
import { ArrowUpRight, Building2, Link2 } from "lucide-react";
import { DataError } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { connectBroker } from "@/features/dashboard/api/dashboard-api";
import { useDashboardSnapshot } from "@/features/dashboard/hooks/use-dashboard-data";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";

const providers = [
  { id: "fyers" as const, name: "Fyers" },
  { id: "groww" as const, name: "Groww" },
];

function ConnectButton({
  provider,
}: {
  provider: { id: "fyers" | "groww"; name: string };
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConnect() {
    setBusy(true);
    setError(null);

    try {
      const redirectUrl = await connectBroker(provider.id);

      console.log("Redirect URL:", redirectUrl);

      window.location.assign(redirectUrl);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Could not start broker connection."
      );

      setBusy(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleConnect}
        disabled={busy}
        className="inline-flex h-10 w-fit items-center gap-2 rounded-lg border border-[var(--line-strong)] px-3.5 text-[13px] font-medium text-[var(--ink)] outline-none transition hover:border-[var(--accent)] hover:text-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--focus)] disabled:cursor-wait disabled:opacity-60"
      >
        {busy ? "Starting connection…" : `Connect ${provider.name}`}
        <ArrowUpRight size={15} />
      </button>

      {error && (
        <p className="mt-2 max-w-sm text-[12px] leading-5 text-[var(--danger)]">
          {error}
        </p>
      )}
    </div>
  );
}

export function BrokerPage() {
  const { data, isLoading, isError } = useDashboardSnapshot();

  const connectedProvider = data?.broker?.provider?.toLowerCase();
  const connectionStatus = data?.broker?.status;

  return (
    <div>
      <WorkspacePageTitle eyebrow="BROKER" title="Broker connection">
        Connect a supported broker through its secure authorization flow.
        Credentials are handled by the broker connection service, not stored in
        this interface.
      </WorkspacePageTitle>

      {isError && (
        <div className="mb-4">
          <DataError message="Broker connection status is unavailable. You can retry once the account service reconnects." />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {providers.map((provider) => {
          const isConnected = connectedProvider === provider.id;

          return (
            <SectionCard key={provider.id} className="flex min-h-60 flex-col">
              <SectionCardHeader
                eyebrow="SUPPORTED BROKER"
                title={provider.name}
              />

              <div className="flex flex-1 flex-col p-5">
                <div className="mb-8 grid h-10 w-10 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
                  <Building2 size={19} />
                </div>

                <p className="text-[13px] font-medium text-[var(--ink)]">
                  {isLoading
                    ? "Checking connection"
                    : isConnected
                    ? connectionStatus || "Connection status available"
                    : "Connection status unavailable"}
                </p>

                <p className="mt-2 max-w-sm text-[12px] leading-5 text-[var(--ink-muted)]">
                  {isConnected
                    ? "This provider is reported by the account service."
                    : "Start the secure broker authorization flow when this provider is available for your account."}
                </p>

                <div className="mt-auto">
                  {!isConnected && (
                    <ConnectButton provider={provider} />
                  )}
                </div>
              </div>
            </SectionCard>
          );
        })}
      </div>

      <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] px-4 py-3.5 text-[12px] leading-5 text-[var(--ink-muted)]">
        <Link2
          size={16}
          className="mt-0.5 shrink-0 text-[var(--accent)]"
        />
        <span>
          Connection authorization opens through the broker API. The dashboard
          displays only the resulting connection status.
        </span>
      </div>
    </div>
  );
}