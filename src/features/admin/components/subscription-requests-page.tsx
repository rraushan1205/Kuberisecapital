"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock, XCircle, IndianRupee } from "lucide-react";
import { Button } from "@/components/ui/button";
import { authHeader } from "@/lib/session-storage";
import { AdminPageTitle } from "./admin-page-title";
import { AdminDataState } from "./admin-data-state";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

type SubscriptionRequestDetail = {
  id: string;
  user_id: string;
  user_email: string;
  user_full_name: string | null;
  plan_tier: string;
  plan_capital: number;
  current_plan_tier: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED";
  requested_at: string;
  reviewed_at: string | null;
  reviewed_by_id: string | null;
  notes: string | null;
};

const tierDisplayNames: Record<string, string> = {
  BASIC: "Basic",
  PLUS: "Plus",
  PRO: "Pro",
  ELITE: "Elite",
  MAX: "Max",
};

export function SubscriptionRequestsPage() {
  const [requests, setRequests] = useState<SubscriptionRequestDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    fetchRequests();
  }, []);

  async function fetchRequests() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/subscription-requests`, {
        credentials: "include",
        headers: { Accept: "application/json", ...authHeader("admin") },
      });

      if (response.ok) {
        const data = await response.json();
        setRequests(data);
      }
    } catch (error) {
      console.error("Failed to fetch subscription requests:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(requestId: string) {
    const notes = prompt("Optional notes for approval:");
    if (notes === null) return; // User cancelled

    setProcessingId(requestId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/subscription-requests/${requestId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader("admin") },
        credentials: "include",
        body: JSON.stringify({ notes: notes.trim() || null }),
      });

      if (response.ok) {
        await fetchRequests();
      } else {
        const error = await response.json();
        alert(error.detail || "Failed to approve request");
      }
    } catch (error) {
      console.error("Failed to approve request:", error);
      alert("Failed to approve request");
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReject(requestId: string) {
    const notes = prompt("Reason for rejection (required):");
    if (!notes || notes.trim() === "") {
      alert("Rejection reason is required");
      return;
    }

    setProcessingId(requestId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/subscription-requests/${requestId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader("admin") },
        credentials: "include",
        body: JSON.stringify({ notes: notes.trim() }),
      });

      if (response.ok) {
        await fetchRequests();
      } else {
        const error = await response.json();
        alert(error.detail || "Failed to reject request");
      }
    } catch (error) {
      console.error("Failed to reject request:", error);
      alert("Failed to reject request");
    } finally {
      setProcessingId(null);
    }
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat("en-IN").format(amount);
  }

  const pendingRequests = requests.filter((r) => r.status === "PENDING");
  const processedRequests = requests.filter((r) => r.status !== "PENDING");

  if (loading) {
    return (
      <div className="space-y-6">
        <AdminPageTitle
          title="Subscription Requests"
          description="Review and approve user subscription plan requests"
        />
        <AdminDataState state="loading" />
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <div className="space-y-6">
        <AdminPageTitle
          title="Subscription Requests"
          description="Review and approve user subscription plan requests"
        />
        <AdminDataState state="empty" emptyMessage="No subscription requests yet" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <AdminPageTitle
        title="Subscription Requests"
        description="Review and approve user subscription plan requests"
      />

      {/* Pending Requests */}
      {pendingRequests.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-5 w-5 text-amber-600" />
            <h2 className="text-lg font-semibold">Pending Requests ({pendingRequests.length})</h2>
          </div>
          <div className="rounded-lg border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-sm font-medium">User</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Current Plan</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Requested Plan</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Capital</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Requested</th>
                    <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingRequests.map((request) => {
                    const isProcessing = processingId === request.id;

                    return (
                      <tr key={request.id} className="border-b last:border-0 hover:bg-muted/30">
                        <td className="px-4 py-3">
                          <div>
                            <div className="font-medium">{request.user_full_name || "N/A"}</div>
                            <div className="text-sm text-muted-foreground">{request.user_email}</div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {request.current_plan_tier ? (
                            <span className="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-950 px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-300">
                              {tierDisplayNames[request.current_plan_tier] || request.current_plan_tier}
                            </span>
                          ) : (
                            <span className="text-sm text-muted-foreground">None</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center rounded-md bg-purple-50 dark:bg-purple-950 px-2 py-1 text-xs font-medium text-purple-700 dark:text-purple-300">
                            {tierDisplayNames[request.plan_tier] || request.plan_tier}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            <IndianRupee className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="font-medium">{formatCurrency(request.plan_capital)}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {new Date(request.requested_at).toLocaleDateString("en-IN", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleReject(request.id)}
                              disabled={isProcessing}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                            >
                              <XCircle className="h-4 w-4 mr-1" />
                              Reject
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleApprove(request.id)}
                              disabled={isProcessing}
                              className="bg-green-600 hover:bg-green-700"
                            >
                              <CheckCircle2 className="h-4 w-4 mr-1" />
                              Approve
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Processed Requests */}
      {processedRequests.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent History</h2>
          <div className="rounded-lg border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-sm font-medium">User</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Plan</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Reviewed</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {processedRequests.slice(0, 20).map((request) => {
                    const statusIcon =
                      request.status === "APPROVED" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600" />
                      );

                    const statusColor =
                      request.status === "APPROVED"
                        ? "text-green-700 dark:text-green-400"
                        : "text-red-700 dark:text-red-400";

                    return (
                      <tr key={request.id} className="border-b last:border-0">
                        <td className="px-4 py-3">
                          <div>
                            <div className="font-medium text-sm">{request.user_full_name || "N/A"}</div>
                            <div className="text-xs text-muted-foreground">{request.user_email}</div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm font-medium">
                            {tierDisplayNames[request.plan_tier] || request.plan_tier}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            {statusIcon}
                            <span className={`text-sm font-medium ${statusColor}`}>
                              {request.status}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {request.reviewed_at
                            ? new Date(request.reviewed_at).toLocaleDateString("en-IN", {
                                year: "numeric",
                                month: "short",
                                day: "numeric",
                              })
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {request.notes || "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
