"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowUpRight, Building2, Link2, CheckCircle2, XCircle } from "lucide-react";
import { DataError } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { connectBroker } from "@/features/dashboard/api/dashboard-api";
import { useDashboardSnapshot } from "@/features/dashboard/hooks/use-dashboard-data";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";

const providers = [
  { id: "fyers" as const, name: "Fyers" },
  { id: "aliceblue" as const, name: "Alice Blue" },
];

export function BrokerPage() {
  const { data, isLoading, isError, refetch } = useDashboardSnapshot();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  
  const connectedProvider = data?.broker?.provider?.toLowerCase();
  const connectionStatus = data?.broker?.status;

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    try {
      await connectBroker(provider);
      // If successful, user will be redirected to broker OAuth page
    } catch (error) {
      setConnecting(null);
      setNotification({
        type: "error",
        message: error instanceof Error ? error.message : "Failed to connect to broker. Please try again.",
      });
    }
  };

  // Handle OAuth callback parameters
  useEffect(() => {
    const connected = searchParams.get("connected");
    const error = searchParams.get("error");
    const provider = searchParams.get("provider");

    if (connected === "true" && provider) {
      setNotification({
        type: "success",
        message: `Successfully connected to ${provider.charAt(0).toUpperCase() + provider.slice(1)}! Your broker account is now linked.`,
      });
      // Refresh dashboard data to show new connection
      refetch();
      // Clear URL parameters
      router.replace("/dashboard/broker");
    } else if (error && provider) {
      let errorMessage = `Failed to connect to ${provider.charAt(0).toUpperCase() + provider.slice(1)}.`;
      if (error === "broker_auth_failed") {
        errorMessage += " Authorization failed. Please try again.";
      } else if (error === "unsupported_provider") {
        errorMessage += " This broker is not supported.";
      } else {
        errorMessage += " An unexpected error occurred.";
      }
      setNotification({
        type: "error",
        message: errorMessage,
      });
      // Clear URL parameters
      router.replace("/dashboard/broker");
    }
  }, [searchParams, router, refetch]);

  // Auto-dismiss notification after 8 seconds
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => {
        setNotification(null);
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  return (
    <div>
      <WorkspacePageTitle eyebrow="BROKER" title="Broker connection">Connect a supported broker through its secure authorization flow. Credentials are handled by the broker connection service, not stored in this interface.</WorkspacePageTitle>
      
      {/* Success/Error Notification */}
      {notification && (
        <div className={`mb-4 flex items-start gap-3 rounded-lg border p-4 ${
          notification.type === "success"
            ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/20"
            : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/20"
        }`}>
          {notification.type === "success" ? (
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
          ) : (
            <XCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
          )}
          <div className="flex-1">
            <p className={`text-sm font-medium ${
              notification.type === "success"
                ? "text-green-900 dark:text-green-100"
                : "text-red-900 dark:text-red-100"
            }`}>
              {notification.type === "success" ? "Connection Successful" : "Connection Failed"}
            </p>
            <p className={`text-sm mt-1 ${
              notification.type === "success"
                ? "text-green-700 dark:text-green-300"
                : "text-red-700 dark:text-red-300"
            }`}>
              {notification.message}
            </p>
          </div>
          <button
            onClick={() => setNotification(null)}
            className={`text-sm font-medium hover:underline ${
              notification.type === "success"
                ? "text-green-700 dark:text-green-300"
                : "text-red-700 dark:text-red-300"
            }`}
          >
            Dismiss
          </button>
        </div>
      )}
      
      {isError && <div className="mb-4"><DataError message="Broker connection status is unavailable. You can retry once the account service reconnects." /></div>}
      <div className="grid gap-4 md:grid-cols-2">
        {providers.map((provider) => {
          const isConnected = connectedProvider === provider.id;
          return (
            <SectionCard key={provider.id} className="flex min-h-60 flex-col">
              <SectionCardHeader eyebrow="SUPPORTED BROKER" title={provider.name} />
              <div className="flex flex-1 flex-col p-5">
                <div className="mb-8 grid h-10 w-10 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]"><Building2 size={19} /></div>
                <p className="text-[13px] font-medium text-[var(--ink)]">{isLoading ? "Checking connection" : isConnected ? connectionStatus || "Connection status available" : "Connection status unavailable"}</p>
                <p className="mt-2 max-w-sm text-[12px] leading-5 text-[var(--ink-muted)]">{isConnected ? "This provider is reported by the account service." : "Start the secure broker authorization flow when this provider is available for your account."}</p>
                <button 
                  onClick={() => handleConnect(provider.id)}
                  disabled={connecting === provider.id}
                  className="mt-auto inline-flex h-10 w-fit items-center gap-2 rounded-lg border border-[var(--line-strong)] px-3.5 text-[13px] font-medium text-[var(--ink)] outline-none transition hover:border-[var(--accent)] hover:text-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--focus)] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {connecting === provider.id ? "Connecting..." : `Connect ${provider.name}`} <ArrowUpRight size={15} />
                </button>
              </div>
            </SectionCard>
          );
        })}
      </div>
      <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-[var(--line)] bg-[var(--panel-raised)] px-4 py-3.5 text-[12px] leading-5 text-[var(--ink-muted)]"><Link2 size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" /> <span>Connection authorization opens through the broker API. The dashboard displays only the resulting connection status.</span></div>
    </div>
  );
}
