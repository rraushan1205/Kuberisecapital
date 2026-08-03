"use client";

import { Copy, Filter, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { adminApi } from "@/features/admin/api/admin-api";
import type { BrokerAccountsResponse } from "@/features/admin/types";
import { AdminEmpty, AdminError, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { cn } from "@/lib/utils";

function truncateId(id: string): string {
  if (id.length <= 16) return id;
  return `${id.slice(0, 8)}...${id.slice(-8)}`;
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {
    // Silently fail if clipboard access is denied
  });
}

function formatDate(dateString: string | null): string {
  if (!dateString) return "—";
  try {
    return new Date(dateString).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "Invalid date";
  }
}

function isTokenExpiringSoon(expiryDate: string | null): boolean {
  if (!expiryDate) return false;
  try {
    const expiry = new Date(expiryDate);
    const now = new Date();
    const hoursUntilExpiry = (expiry.getTime() - now.getTime()) / (1000 * 60 * 60);
    return hoursUntilExpiry > 0 && hoursUntilExpiry < 24;
  } catch {
    return false;
  }
}

function isTokenExpired(expiryDate: string | null): boolean {
  if (!expiryDate) return false;
  try {
    return new Date(expiryDate) < new Date();
  } catch {
    return false;
  }
}

export function BrokersPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [data, setData] = useState<BrokerAccountsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Get filters from URL
  const page = Number.parseInt(searchParams.get("page") || "1", 10);
  const limit = Number.parseInt(searchParams.get("limit") || "20", 10);
  const provider = searchParams.get("provider") || "";
  const status = searchParams.get("status") || "";
  const userId = searchParams.get("user_id") || "";

  // Local filter state
  const [filterProvider, setFilterProvider] = useState(provider);
  const [filterStatus, setFilterStatus] = useState(status);
  const [filterUserId, setFilterUserId] = useState(userId);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    setFilterProvider(provider);
    setFilterStatus(status);
    setFilterUserId(userId);
  }, [provider, status, userId]);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setIsError(false);
      try {
        const skip = (page - 1) * limit;
        const response = await adminApi.getBrokerAccounts(
          skip,
          limit,
          provider || undefined,
          status || undefined,
          userId || undefined
        );
        setData(response);
      } catch {
        setIsError(true);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [page, limit, provider, status, userId]);

  const updateUrl = (updates: Record<string, string>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
    });
    // Reset to page 1 when filters change
    if (updates.provider !== undefined || updates.status !== undefined || updates.user_id !== undefined) {
      params.set("page", "1");
    }
    router.push(`/admin/brokers?${params.toString()}`);
  };

  const applyFilters = () => {
    updateUrl({
      provider: filterProvider,
      status: filterStatus,
      user_id: filterUserId,
    });
    setShowFilters(false);
  };

  const clearFilters = () => {
    setFilterProvider("");
    setFilterStatus("");
    setFilterUserId("");
    updateUrl({
      provider: "",
      status: "",
      user_id: "",
    });
    setShowFilters(false);
  };

  const hasActiveFilters = provider || status || userId;

  const handleCopy = (id: string, text: string) => {
    copyToClipboard(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const totalPages = data ? Math.ceil(data.total / limit) : 0;
  const startIndex = data ? (page - 1) * limit + 1 : 0;
  const endIndex = data ? Math.min(page * limit, data.total) : 0;

  return (
    <div>
      <AdminPageTitle eyebrow="BROKER MANAGEMENT" title="Broker accounts">
        View and monitor all broker connections across the platform with filtering and search capabilities.
      </AdminPageTitle>

      <SectionCard>
        <SectionCardHeader
          eyebrow="CONNECTION RECORDS"
          title="Broker Accounts"
          action={
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="relative"
            >
              <Filter size={14} />
              Filters
              {hasActiveFilters && (
                <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-[var(--danger)]" />
              )}
            </Button>
          }
        />

        {showFilters && (
          <div className="border-b border-[var(--line)] bg-[var(--panel-raised)] p-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="mb-1.5 block font-mono text-[10px] font-medium uppercase tracking-[0.09em] text-[var(--ink-subtle)]">
                  Provider
                </label>
                <select
                  value={filterProvider}
                  onChange={(e) => setFilterProvider(e.target.value)}
                  className="w-full rounded-md border border-[var(--line)] bg-[var(--canvas)] px-3 py-2 text-[12px] text-[var(--ink)] outline-none focus:ring-2 focus:ring-[var(--focus)]"
                >
                  <option value="">All providers</option>
                  <option value="fyers">Fyers</option>
                  <option value="zerodha">Zerodha</option>
                  <option value="upstox">Upstox</option>
                  <option value="angelone">Angel One</option>
                </select>
              </div>

              <div>
                <label className="mb-1.5 block font-mono text-[10px] font-medium uppercase tracking-[0.09em] text-[var(--ink-subtle)]">
                  Status
                </label>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="w-full rounded-md border border-[var(--line)] bg-[var(--canvas)] px-3 py-2 text-[12px] text-[var(--ink)] outline-none focus:ring-2 focus:ring-[var(--focus)]"
                >
                  <option value="">All statuses</option>
                  <option value="connected">Connected</option>
                  <option value="disconnected">Disconnected</option>
                </select>
              </div>

              <div>
                <label className="mb-1.5 block font-mono text-[10px] font-medium uppercase tracking-[0.09em] text-[var(--ink-subtle)]">
                  User ID
                </label>
                <input
                  type="text"
                  value={filterUserId}
                  onChange={(e) => setFilterUserId(e.target.value)}
                  placeholder="Enter user ID"
                  className="w-full rounded-md border border-[var(--line)] bg-[var(--canvas)] px-3 py-2 text-[12px] text-[var(--ink)] placeholder:text-[var(--ink-subtle)] outline-none focus:ring-2 focus:ring-[var(--focus)]"
                />
              </div>

              <div className="flex items-end gap-2">
                <Button variant="primary" size="sm" onClick={applyFilters} className="flex-1">
                  Apply
                </Button>
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear
                </Button>
              </div>
            </div>
          </div>
        )}

        {isLoading ? (
          <AdminLoadingRows />
        ) : isError ? (
          <div className="p-5">
            <AdminError message="Broker account records could not be loaded." />
          </div>
        ) : !data?.items.length ? (
          <AdminEmpty message={hasActiveFilters ? "No broker accounts match the current filters." : "No broker accounts are available."} />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-[1000px] w-full text-left">
                <thead className="border-b border-[var(--line)] bg-[var(--panel-raised)] font-mono text-[10px] uppercase tracking-[0.09em] text-[var(--ink-subtle)]">
                  <tr>
                    <th className="px-5 py-3 font-medium">Broker User ID</th>
                    <th className="px-5 py-3 font-medium">Provider</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">User ID</th>
                    <th className="px-5 py-3 font-medium">Connected At</th>
                    <th className="px-5 py-3 font-medium">Token Expires</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {data.items.map((account) => (
                    <tr key={account.id} className="text-[12px] hover:bg-[var(--panel-raised)]/50">
                      <td className="px-5 py-3.5">
                        <p className="font-medium text-[var(--ink)]">
                          {account.broker_user_id || "—"}
                        </p>
                      </td>
                      <td className="px-5 py-3.5">
                        <p className="capitalize text-[var(--ink-muted)]">{account.provider}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
                            account.status === "connected"
                              ? "bg-green-500/10 text-green-600 dark:text-green-400"
                              : "bg-gray-500/10 text-gray-600 dark:text-gray-400"
                          )}
                        >
                          {account.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <button
                          onClick={() => handleCopy(account.id, account.user_id)}
                          className="group flex items-center gap-1.5 text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors"
                          title="Click to copy full ID"
                        >
                          <span className="font-mono text-[11px]">
                            {truncateId(account.user_id)}
                          </span>
                          <Copy
                            size={12}
                            className={cn(
                              "opacity-0 group-hover:opacity-100 transition-opacity",
                              copiedId === account.id && "opacity-100 text-green-600"
                            )}
                          />
                        </button>
                      </td>
                      <td className="px-5 py-3.5 text-[var(--ink-muted)]">
                        {formatDate(account.connected_at)}
                      </td>
                      <td className="px-5 py-3.5">
                        {account.token_expires_at ? (
                          <span
                            className={cn(
                              "text-[var(--ink-muted)]",
                              isTokenExpired(account.token_expires_at) &&
                                "text-red-600 dark:text-red-400 font-medium",
                              isTokenExpiringSoon(account.token_expires_at) &&
                                !isTokenExpired(account.token_expires_at) &&
                                "text-orange-600 dark:text-orange-400 font-medium"
                            )}
                            title={
                              isTokenExpired(account.token_expires_at)
                                ? "Token expired"
                                : isTokenExpiringSoon(account.token_expires_at)
                                ? "Expires within 24 hours"
                                : undefined
                            }
                          >
                            {formatDate(account.token_expires_at)}
                          </span>
                        ) : (
                          <span className="text-[var(--ink-muted)]">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-[var(--line)] px-5 py-4">
              <p className="text-[12px] text-[var(--ink-muted)]">
                Showing {startIndex} to {endIndex} of {data.total} results
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateUrl({ page: (page - 1).toString() })}
                  disabled={page <= 1}
                >
                  Previous
                </Button>
                <span className="px-3 text-[12px] text-[var(--ink-muted)]">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateUrl({ page: (page + 1).toString() })}
                  disabled={page >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </SectionCard>
    </div>
  );
}
