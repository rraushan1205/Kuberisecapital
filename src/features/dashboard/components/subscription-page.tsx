"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock, XCircle, IndianRupee } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  BASIC: "from-slate-500 to-slate-600",
  PLUS: "from-blue-500 to-blue-600",
  PRO: "from-purple-500 to-purple-600",
  ELITE: "from-amber-500 to-amber-600",
  MAX: "from-rose-500 to-rose-600",
};

export function SubscriptionPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [requests, setRequests] = useState<SubscriptionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestingPlanId, setRequestingPlanId] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      setError(null);
      const [plansRes, requestsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/client/subscription/plans`, { credentials: "include" }),
        fetch(`${API_BASE_URL}/api/v1/client/subscription/my-requests`, { credentials: "include" }),
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
        headers: { "Content-Type": "application/json" },
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

  function getPlanRequestStatus(planId: string): SubscriptionRequest | undefined {
    return requests.find((r) => r.plan_id === planId && r.status === "PENDING");
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

      {/* Plans Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan) => {
          const pendingRequest = getPlanRequestStatus(plan.id);
          const isRequesting = requestingPlanId === plan.id;

          return (
            <div
              key={plan.id}
              className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col"
            >
              {/* Header with gradient */}
              <div
                className={`bg-gradient-to-br ${
                  tierColors[plan.tier] || "from-gray-500 to-gray-600"
                } p-6 text-white`}
              >
                <h3 className="text-2xl font-bold">{tierDisplayNames[plan.tier] || plan.tier}</h3>
                <div className="flex items-baseline gap-1 mt-2">
                  <IndianRupee className="h-5 w-5" />
                  <span className="text-3xl font-bold">{formatCurrency(plan.capital)}</span>
                </div>
                <p className="text-sm opacity-90 mt-1">Capital Requirement</p>
              </div>

              {/* Plan Details */}
              <div className="p-6 flex-1">
                <div className="space-y-3">
                  <div className="flex justify-between items-center py-2 border-b">
                    <span className="text-sm text-muted-foreground">Nifty Lots</span>
                    <span className="font-semibold">{plan.nifty_lots}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b">
                    <span className="text-sm text-muted-foreground">Sensex Lots</span>
                    <span className="font-semibold">{plan.sensex_lots}</span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-sm text-muted-foreground">Bank Nifty Lots</span>
                    <span className="font-semibold">{plan.bank_nifty_lots}</span>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="p-6 pt-0">
                {pendingRequest ? (
                  <div className="flex items-center justify-center gap-2 py-3 px-4 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-300 rounded-md border border-amber-200 dark:border-amber-900">
                    <Clock className="h-4 w-4" />
                    <span className="text-sm font-medium">Pending Approval</span>
                  </div>
                ) : (
                  <Button
                    onClick={() => handleRequestPlan(plan.id)}
                    disabled={isRequesting}
                    className="w-full"
                    size="lg"
                  >
                    {isRequesting ? "Requesting..." : "Request Plan"}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
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
