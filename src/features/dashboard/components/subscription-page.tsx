"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock, XCircle, IndianRupee, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { authHeader } from "@/lib/session-storage";
import { WorkspacePageTitle } from "./workspace-page-title";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

type SubscriptionPlan = {
  id: string;
  tier: string;
  capital: number;
  nifty_lots: number;
  sensex_lots: number;
  bank_nifty_lots: number;
  is_active: boolean;
};

type SubscriptionRequest = {
  id: string;
  user_id: string;
  plan_id: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  requested_at: string;
  reviewed_at: string | null;
  notes: string | null;
};

const tierDisplayNames: Record<string, string> = {
  BASIC: "Basic",
  PLUS: "Plus",
  PRO: "Pro",
  ELITE: "Elite",
  MAX: "Max",
};

const tierColors: Record<string, string> = {
  BASIC: "from-slate-400/90 to-slate-500/90",
  PLUS: "from-blue-400/90 to-blue-500/90",
  PRO: "from-violet-400/90 to-violet-500/90",
  ELITE: "from-amber-400/90 to-amber-500/90",
  MAX: "from-rose-400/90 to-rose-500/90",
};

// Mapping capital values to determine upgrade/downgrade
const tierOrder = ["BASIC", "PLUS", "PRO", "ELITE", "MAX"];

export function SubscriptionPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [requests, setRequests] = useState<SubscriptionRequest[]>([]);
  const [currentPlan, setCurrentPlan] = useState<SubscriptionPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestingPlanId, setRequestingPlanId] = useState<string | null>(null);
  const [cancelingRequestId, setCancelingRequestId] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      setError(null);
      const [plansRes, requestsRes, currentPlanRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/client/subscription/plans`, { credentials: "include", headers: { Accept: "application/json", ...authHeader() } }),
        fetch(`${API_BASE_URL}/api/v1/client/subscription/my-requests`, { credentials: "include", headers: { Accept: "application/json", ...authHeader() } }),
        fetch(`${API_BASE_URL}/api/v1/client/subscription/current-plan`, { credentials: "include", headers: { Accept: "application/json", ...authHeader() } }),
      ]);

      if (!plansRes.ok) {
        const errorText = await plansRes.text();
        console.error("Failed to fetch plans:", plansRes.status, errorText);
        setError(`Failed to load subscription plans. Backend may need database migration.`);
        return;
      }

      if (!requestsRes.ok) {
        const errorText = await requestsRes.text();
        console.error("Failed to fetch requests:", requestsRes.status, errorText);
      }

      const plansData = await plansRes.json();
      setPlans(plansData);

      if (requestsRes.ok) {
        const requestsData = await requestsRes.json();
        setRequests(requestsData);
      }

      if (currentPlanRes.ok) {
        const currentPlanData = await currentPlanRes.json();
        setCurrentPlan(currentPlanData);
      }
    } catch (error) {
      console.error("Failed to fetch subscription data:", error);
      setError("Failed to connect to backend server. Please ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestPlan(planId: string) {
    setRequestingPlanId(planId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/client/subscription/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        credentials: "include",
        body: JSON.stringify({ plan_id: planId }),
      });

      if (response.ok) {
        // Refresh requests
        await fetchData();
      } else {
        const error = await response.json();
        alert(error.detail || "Failed to request plan");
      }
    } catch (error) {
      console.error("Failed to request plan:", error);
      alert("Failed to request plan");
    } finally {
      setRequestingPlanId(null);
    }
  }

  async function handleCancelRequest(requestId: string) {
    if (!confirm("Are you sure you want to cancel this subscription request?")) {
      return;
    }

    setCancelingRequestId(requestId);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/client/subscription/request/${requestId}`, {
        method: "DELETE",
        credentials: "include",
        headers: { Accept: "application/json", ...authHeader() },
      });

      if (response.ok) {
        // Refresh data
        await fetchData();
      } else {
        const error = await response.json();
        alert(error.detail || "Failed to cancel request");
      }
    } catch (error) {
      console.error("Failed to cancel request:", error);
      alert("Failed to cancel request");
    } finally {
      setCancelingRequestId(null);
    }
  }

  function getPlanRequestStatus(planId: string): SubscriptionRequest | undefined {
    return requests.find((r) => r.plan_id === planId && r.status === "PENDING");
  }

  function isCurrentPlan(planId: string): boolean {
    return currentPlan?.id === planId;
  }

  function getButtonState(plan: SubscriptionPlan): {
    label: string;
    variant: "default" | "secondary" | "outline" | "quiet";
    disabled: boolean;
    action: (() => void) | null;
  } {
    const pendingRequest = getPlanRequestStatus(plan.id);
    const isRequesting = requestingPlanId === plan.id;

    // Current active plan
    if (isCurrentPlan(plan.id)) {
      return {
        label: "Current Plan",
        variant: "secondary",
        disabled: true,
        action: null,
      };
    }

    // Pending request for this plan
    if (pendingRequest) {
      return {
        label: "Pending Approval",
        variant: "outline",
        disabled: false,
        action: () => handleCancelRequest(pendingRequest.id),
      };
    }

    // Determine if upgrade or downgrade
    if (currentPlan) {
      const currentIndex = tierOrder.indexOf(currentPlan.tier);
      const targetIndex = tierOrder.indexOf(plan.tier);

      if (targetIndex > currentIndex) {
        return {
          label: isRequesting ? "Requesting..." : "Upgrade Plan",
          variant: "default",
          disabled: isRequesting,
          action: () => handleRequestPlan(plan.id),
        };
      } else {
        return {
          label: isRequesting ? "Requesting..." : "Downgrade Plan",
          variant: "default",
          disabled: isRequesting,
          action: () => handleRequestPlan(plan.id),
        };
      }
    }

    // No current plan
    return {
      label: isRequesting ? "Requesting..." : "Request Plan",
      variant: "default",
      disabled: isRequesting,
      action: () => handleRequestPlan(plan.id),
    };
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat("en-IN").format(amount);
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <WorkspacePageTitle
          title="Subscription Plans"
          description="Choose the plan that fits your trading needs"
        />
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">Loading plans...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <WorkspacePageTitle
          title="Subscription Plans"
          description="Choose the plan that fits your trading needs"
        />
        <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/20 p-6">
          <h3 className="font-semibold text-red-900 dark:text-red-100 mb-2">
            Unable to Load Subscription Plans
          </h3>
          <p className="text-sm text-red-700 dark:text-red-300 mb-4">{error}</p>
          <div className="text-sm text-red-600 dark:text-red-400">
            <p className="font-medium mb-2">To fix this issue:</p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Ensure the backend server is running</li>
              <li>Run the database migration: <code className="bg-red-100 dark:bg-red-900 px-1 py-0.5 rounded">cd backend && python3 -m alembic upgrade head</code></li>
              <li>Refresh this page</li>
            </ol>
          </div>
          <button
            onClick={() => {
              setLoading(true);
              fetchData();
            }}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (plans.length === 0) {
    return (
      <div className="space-y-6">
        <WorkspacePageTitle
          title="Subscription Plans"
          description="Choose the plan that fits your trading needs"
        />
        <div className="rounded-lg border bg-card p-12 text-center">
          <p className="text-muted-foreground">No subscription plans available at this time.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <WorkspacePageTitle
        title="Subscription Plans"
        description="Choose the plan that fits your trading needs. Request any plan and continue using your current plan until admin approves."
      />

      {/* Active Requests Notice */}
      {requests.filter((r) => r.status === "PENDING").length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/20 p-4">
          <div className="flex items-start gap-3">
            <Clock className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5" />
            <div>
              <h3 className="font-medium text-amber-900 dark:text-amber-100">
                Pending Requests
              </h3>
              <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                You have {requests.filter((r) => r.status === "PENDING").length} pending subscription
                request(s) awaiting admin approval.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Plans - Single Row Horizontal Layout */}
      <div className="overflow-x-auto pb-4">
        <div className="flex gap-4 min-w-max">
          {plans.map((plan) => {
            const buttonState = getButtonState(plan);
            const isCanceling = cancelingRequestId === getPlanRequestStatus(plan.id)?.id;

            return (
              <div
                key={plan.id}
                className="rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col w-64 flex-shrink-0"
              >
                {/* Header with gradient */}
                <div
                  className={`bg-gradient-to-br ${
                    tierColors[plan.tier] || "from-gray-400/90 to-gray-500/90"
                  } p-5 text-white relative`}
                >
                  <h3 className="text-xl font-semibold">{tierDisplayNames[plan.tier] || plan.tier}</h3>
                  <div className="flex items-baseline gap-1 mt-2">
                    <IndianRupee className="h-4 w-4" />
                    <span className="text-2xl font-semibold">{formatCurrency(plan.capital)}</span>
                  </div>
                  <p className="text-xs opacity-90 mt-1">Capital Requirement</p>
                  
                  {/* Current Plan Badge */}
                  {isCurrentPlan(plan.id) && (
                    <div className="absolute top-3 right-3 bg-white/20 backdrop-blur-sm text-white text-xs font-medium px-2 py-1 rounded">
                      Active
                    </div>
                  )}
                </div>

                {/* Plan Details */}
                <div className="p-5 flex-1">
                  <div className="space-y-2.5">
                    <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                      <span className="text-xs text-muted-foreground">Nifty Lots</span>
                      <span className="font-medium text-sm">{plan.nifty_lots}</span>
                    </div>
                    <div className="flex justify-between items-center py-1.5 border-b border-border/40">
                      <span className="text-xs text-muted-foreground">Sensex Lots</span>
                      <span className="font-medium text-sm">{plan.sensex_lots}</span>
                    </div>
                    <div className="flex justify-between items-center py-1.5">
                      <span className="text-xs text-muted-foreground">Bank Nifty Lots</span>
                      <span className="font-medium text-sm">{plan.bank_nifty_lots}</span>
                    </div>
                  </div>
                </div>

                {/* Action Button */}
                <div className="p-5 pt-0">
                  {buttonState.label === "Pending Approval" ? (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-300 rounded-lg border border-amber-200 dark:border-amber-900">
                        <Clock className="h-3.5 w-3.5" />
                        <span className="text-xs font-medium">Pending</span>
                      </div>
                      <Button
                        onClick={buttonState.action || undefined}
                        disabled={isCanceling}
                        variant="quiet"
                        size="sm"
                        className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive"
                        title="Cancel request"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <Button
                      onClick={buttonState.action || undefined}
                      disabled={buttonState.disabled}
                      variant={buttonState.variant}
                      className="w-full"
                      size="sm"
                    >
                      {buttonState.label}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Request History */}
      {requests.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Request History</h2>
          <div className="rounded-lg border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-sm font-medium">Plan</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Requested</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map((request) => {
                    const plan = plans.find((p) => p.id === request.plan_id);
                    const statusIcon =
                      request.status === "APPROVED" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : request.status === "REJECTED" ? (
                        <XCircle className="h-4 w-4 text-red-600" />
                      ) : (
                        <Clock className="h-4 w-4 text-amber-600" />
                      );

                    const statusColor =
                      request.status === "APPROVED"
                        ? "text-green-700 dark:text-green-400"
                        : request.status === "REJECTED"
                        ? "text-red-700 dark:text-red-400"
                        : "text-amber-700 dark:text-amber-400";

                    return (
                      <tr key={request.id} className="border-b last:border-0">
                        <td className="px-4 py-3">
                          <span className="font-medium">
                            {plan ? tierDisplayNames[plan.tier] || plan.tier : "Unknown"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {new Date(request.requested_at).toLocaleDateString("en-IN", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
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
