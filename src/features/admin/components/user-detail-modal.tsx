"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/features/admin/api/admin-api";
import { formatDateTime } from "@/features/admin/lib/format";
import type { AdminUser, AdminUserDetail, AdminSubscriptionPlan } from "@/features/admin/types";

interface UserDetailModalProps {
  user: AdminUser;
  onClose: () => void;
}

export function UserDetailModal({ user, onClose }: UserDetailModalProps) {
  const [userDetail, setUserDetail] = useState<AdminUserDetail | null>(null);
  const [plans, setPlans] = useState<AdminSubscriptionPlan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [showPlanSelector, setShowPlanSelector] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        setError(null);
        const [detail, availablePlans] = await Promise.all([
          adminApi.getUserDetail(user.id),
          adminApi.getSubscriptionPlans(),
        ]);
        setUserDetail(detail);
        setPlans(availablePlans.filter((p) => p.is_active));
        setSelectedPlanId(detail.current_plan_id || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load user details");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [user.id]);

  const handleUpdateSubscription = async () => {
    if (!selectedPlanId || !userDetail) return;

    try {
      setIsUpdating(true);
      setError(null);
      const updated = await adminApi.updateUserSubscription(user.id, {
        plan_id: selectedPlanId,
        notes: notes.trim() || undefined,
      });
      setUserDetail(updated);
      setShowPlanSelector(false);
      setNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update subscription");
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-[var(--panel)] border border-[var(--line)] rounded-lg shadow-xl">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[var(--panel)] border-b border-[var(--line)] px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[var(--ink)]">User Details</h2>
            <p className="text-sm text-[var(--ink-muted)] mt-0.5">{user.email}</p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--ink-muted)] hover:text-[var(--ink)] text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {isLoading ? (
            <div className="text-center py-12 text-[var(--ink-muted)]">Loading user details...</div>
          ) : error ? (
            <div className="bg-red-500/10 border border-red-500/20 rounded p-4 text-red-600 text-sm">
              {error}
            </div>
          ) : userDetail ? (
            <>
              {/* Basic Information */}
              <section>
                <h3 className="text-sm font-mono uppercase tracking-wider text-[var(--ink-subtle)] mb-3">
                  Account Information
                </h3>
                <div className="grid grid-cols-2 gap-4 bg-[var(--panel-raised)] rounded-lg p-4">
                  <InfoField label="Full Name" value={userDetail.full_name || "Not provided"} />
                  <InfoField label="Email" value={userDetail.email} />
                  <InfoField label="Role" value={userDetail.role} />
                  <InfoField
                    label="Email Verified"
                    value={userDetail.email_verified ? "Yes" : "No"}
                  />
                  <InfoField label="Account Status" value={userDetail.account_status} />
                  <InfoField label="Subscription Status" value={userDetail.subscription_status} />
                  <InfoField
                    label="Registered"
                    value={formatDateTime(userDetail.created_at)}
                  />
                  <InfoField
                    label="Last Login"
                    value={formatDateTime(userDetail.last_login_at)}
                  />
                </div>
              </section>

              {/* Current Subscription Plan */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-mono uppercase tracking-wider text-[var(--ink-subtle)]">
                    Current Subscription Plan
                  </h3>
                  {!showPlanSelector && userDetail.role === "USER" && (
                    <button
                      onClick={() => setShowPlanSelector(true)}
                      className="text-xs px-3 py-1.5 bg-[var(--ink)] text-[var(--panel)] rounded hover:opacity-90"
                    >
                      Change Plan
                    </button>
                  )}
                </div>

                {userDetail.current_plan_tier ? (
                  <div className="bg-[var(--panel-raised)] rounded-lg p-4">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <p className="text-lg font-semibold text-[var(--ink)]">
                          {userDetail.current_plan_tier}
                        </p>
                        <p className="text-sm text-[var(--ink-muted)] mt-1">
                          Capital: ₹{userDetail.current_plan_capital?.toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-[var(--ink-muted)]">Nifty Lots</p>
                        <p className="font-medium text-[var(--ink)] mt-1">
                          {userDetail.current_plan_nifty_lots}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--ink-muted)]">Sensex Lots</p>
                        <p className="font-medium text-[var(--ink)] mt-1">
                          {userDetail.current_plan_sensex_lots}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--ink-muted)]">Bank Nifty Lots</p>
                        <p className="font-medium text-[var(--ink)] mt-1">
                          {userDetail.current_plan_bank_nifty_lots}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-[var(--panel-raised)] rounded-lg p-4 text-center text-[var(--ink-muted)]">
                    No active subscription plan
                  </div>
                )}

                {/* Plan Change Interface */}
                {showPlanSelector && (
                  <div className="mt-4 bg-[var(--panel-raised)] rounded-lg p-4 border border-[var(--line)]">
                    <h4 className="text-sm font-medium text-[var(--ink)] mb-3">
                      Update Subscription Plan
                    </h4>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs text-[var(--ink-muted)] mb-2">
                          Select Plan
                        </label>
                        <select
                          value={selectedPlanId}
                          onChange={(e) => setSelectedPlanId(e.target.value)}
                          className="w-full px-3 py-2 bg-[var(--panel)] border border-[var(--line)] rounded text-sm text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--ink)]/20"
                        >
                          <option value="">Select a plan...</option>
                          {plans.map((plan) => (
                            <option key={plan.id} value={plan.id}>
                              {plan.tier} - ₹{plan.capital.toLocaleString()} (Nifty: {plan.nifty_lots}, Sensex: {plan.sensex_lots}, Bank Nifty: {plan.bank_nifty_lots})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-[var(--ink-muted)] mb-2">
                          Notes (optional)
                        </label>
                        <textarea
                          value={notes}
                          onChange={(e) => setNotes(e.target.value)}
                          placeholder="Add any notes about this subscription change..."
                          rows={3}
                          className="w-full px-3 py-2 bg-[var(--panel)] border border-[var(--line)] rounded text-sm text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--ink)]/20 resize-none"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={handleUpdateSubscription}
                          disabled={!selectedPlanId || isUpdating}
                          className="px-4 py-2 bg-[var(--ink)] text-[var(--panel)] rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isUpdating ? "Updating..." : "Update Plan"}
                        </button>
                        <button
                          onClick={() => {
                            setShowPlanSelector(false);
                            setSelectedPlanId(userDetail.current_plan_id || "");
                            setNotes("");
                          }}
                          disabled={isUpdating}
                          className="px-4 py-2 bg-[var(--panel-raised)] text-[var(--ink)] border border-[var(--line)] rounded text-sm font-medium hover:bg-[var(--panel-hover)]"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </section>

              {/* Pending Subscription Request */}
              {userDetail.pending_request_id && (
                <section>
                  <h3 className="text-sm font-mono uppercase tracking-wider text-[var(--ink-subtle)] mb-3">
                    Pending Subscription Request
                  </h3>
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                    <p className="text-sm text-[var(--ink)]">
                      User has requested an upgrade to{" "}
                      <span className="font-semibold">{userDetail.pending_request_plan_tier}</span> plan
                    </p>
                    <p className="text-xs text-[var(--ink-muted)] mt-2">
                      Review this request in the Subscription Requests section
                    </p>
                  </div>
                </section>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-[var(--ink-muted)]">{label}</p>
      <p className="text-sm font-medium text-[var(--ink)] mt-1">{value}</p>
    </div>
  );
}
