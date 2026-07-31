"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { Edit2, LoaderCircle, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { useSubscriptionPlans, useCreateSubscriptionPlan, useUpdateSubscriptionPlan, useDeleteSubscriptionPlan } from "@/features/admin/hooks/use-admin-data";
import type { AdminSubscriptionPlan, SubscriptionPlanTier } from "@/features/admin/types";

const planSchema = z.object({
  tier: z.enum(["BASIC", "PLUS", "PRO", "ELITE", "MAX"], { required_error: "Select a plan tier." }),
  capital: z.number({ required_error: "Enter capital amount." }).int().positive("Capital must be positive."),
  nifty_lots: z.number({ required_error: "Enter Nifty lots." }).int().min(0, "Nifty lots cannot be negative."),
  sensex_lots: z.number({ required_error: "Enter Sensex lots." }).int().min(0, "Sensex lots cannot be negative."),
  bank_nifty_lots: z.number({ required_error: "Enter Bank Nifty lots." }).int().min(0, "Bank Nifty lots cannot be negative."),
  is_active: z.boolean(),
});

type PlanValues = z.infer<typeof planSchema>;

function PlanDialog({ 
  mode, 
  plan, 
  open, 
  onOpenChange 
}: { 
  mode: "create" | "edit"; 
  plan?: AdminSubscriptionPlan; 
  open: boolean; 
  onOpenChange: (open: boolean) => void;
}) {
  const create = useCreateSubscriptionPlan();
  const update = useUpdateSubscriptionPlan();
  const mutation = mode === "create" ? create : update;
  
  const form = useForm<PlanValues>({
    resolver: zodResolver(planSchema),
    mode: "onBlur",
    defaultValues: plan ? {
      tier: plan.tier,
      capital: plan.capital,
      nifty_lots: plan.nifty_lots,
      sensex_lots: plan.sensex_lots,
      bank_nifty_lots: plan.bank_nifty_lots,
      is_active: plan.is_active,
    } : {
      tier: "BASIC",
      capital: 100000,
      nifty_lots: 0,
      sensex_lots: 0,
      bank_nifty_lots: 0,
      is_active: true,
    },
  });

  function close(force = false) {
    if (mutation.isPending && !force) return;
    onOpenChange(false);
    form.reset();
  }

  function submit(values: PlanValues) {
    if (mode === "create") {
      create.mutate(values, { onSuccess: () => close(true) });
    } else if (plan) {
      update.mutate({ planId: plan.id, plan: values }, { onSuccess: () => close(true) });
    }
  }

  const isPending = mutation.isPending;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--surface)] rounded-lg shadow-2xl p-6 w-full max-w-md z-50 max-h-[90vh] overflow-y-auto">
          <div className="flex items-start justify-between mb-4">
            <div>
              <Dialog.Title className="text-lg font-semibold text-[var(--ink)]">
                {mode === "create" ? "Create subscription plan" : "Edit subscription plan"}
              </Dialog.Title>
              <Dialog.Description className="text-[13px] text-[var(--ink-muted)] mt-1">
                {mode === "create" ? "Add a new subscription plan for users to select." : "Modify the subscription plan details."}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button className="text-[var(--ink-subtle)] hover:text-[var(--ink)] transition-colors" disabled={isPending}>
                <X size={20} />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={form.handleSubmit(submit)} className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium text-[var(--ink)] mb-1.5">Plan tier</label>
              <select
                {...form.register("tier")}
                disabled={isPending}
                className="w-full px-3 py-2 bg-[var(--surface-raised)] border border-[var(--line)] rounded-md text-[13px] text-[var(--ink)] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              >
                <option value="BASIC">BASIC</option>
                <option value="PLUS">PLUS</option>
                <option value="PRO">PRO</option>
                <option value="ELITE">ELITE</option>
                <option value="MAX">MAX</option>
              </select>
              {form.formState.errors.tier && (
                <p className="text-[12px] text-red-500 mt-1">{form.formState.errors.tier.message}</p>
              )}
            </div>

            <div>
              <label className="block text-[13px] font-medium text-[var(--ink)] mb-1.5">Capital (₹)</label>
              <input
                type="number"
                {...form.register("capital", { valueAsNumber: true })}
                disabled={isPending}
                className="w-full px-3 py-2 bg-[var(--surface-raised)] border border-[var(--line)] rounded-md text-[13px] text-[var(--ink)] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="100000"
              />
              {form.formState.errors.capital && (
                <p className="text-[12px] text-red-500 mt-1">{form.formState.errors.capital.message}</p>
              )}
            </div>

            <div>
              <label className="block text-[13px] font-medium text-[var(--ink)] mb-1.5">Nifty lots</label>
              <input
                type="number"
                {...form.register("nifty_lots", { valueAsNumber: true })}
                disabled={isPending}
                className="w-full px-3 py-2 bg-[var(--surface-raised)] border border-[var(--line)] rounded-md text-[13px] text-[var(--ink)] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="0"
              />
              {form.formState.errors.nifty_lots && (
                <p className="text-[12px] text-red-500 mt-1">{form.formState.errors.nifty_lots.message}</p>
              )}
            </div>

            <div>
              <label className="block text-[13px] font-medium text-[var(--ink)] mb-1.5">Sensex lots</label>
              <input
                type="number"
                {...form.register("sensex_lots", { valueAsNumber: true })}
                disabled={isPending}
                className="w-full px-3 py-2 bg-[var(--surface-raised)] border border-[var(--line)] rounded-md text-[13px] text-[var(--ink)] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="0"
              />
              {form.formState.errors.sensex_lots && (
                <p className="text-[12px] text-red-500 mt-1">{form.formState.errors.sensex_lots.message}</p>
              )}
            </div>

            <div>
              <label className="block text-[13px] font-medium text-[var(--ink)] mb-1.5">Bank Nifty lots</label>
              <input
                type="number"
                {...form.register("bank_nifty_lots", { valueAsNumber: true })}
                disabled={isPending}
                className="w-full px-3 py-2 bg-[var(--surface-raised)] border border-[var(--line)] rounded-md text-[13px] text-[var(--ink)] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="0"
              />
              {form.formState.errors.bank_nifty_lots && (
                <p className="text-[12px] text-red-500 mt-1">{form.formState.errors.bank_nifty_lots.message}</p>
              )}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                {...form.register("is_active")}
                disabled={isPending}
                className="w-4 h-4 rounded border-[var(--line)] text-blue-500 focus:ring-2 focus:ring-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <label htmlFor="is_active" className="text-[13px] font-medium text-[var(--ink)] cursor-pointer">
                Active (visible to users)
              </label>
            </div>

            {form.formState.errors.root && (
              <AdminError message={form.formState.errors.root.message || "An error occurred."} />
            )}

            {mutation.error && (
              <AdminError message={mutation.error.message} />
            )}

            <div className="flex gap-2 pt-2">
              <Button type="button" variant="secondary" size="md" onClick={() => close()} disabled={isPending} className="flex-1">
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="md" disabled={isPending} className="flex-1">
                {isPending ? <LoaderCircle size={16} className="animate-spin" /> : mode === "create" ? "Create plan" : "Save changes"}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function DeleteConfirmDialog({ 
  plan, 
  open, 
  onOpenChange 
}: { 
  plan: AdminSubscriptionPlan; 
  open: boolean; 
  onOpenChange: (open: boolean) => void;
}) {
  const deleteMutation = useDeleteSubscriptionPlan();

  function handleDelete() {
    deleteMutation.mutate(plan.id, {
      onSuccess: () => onOpenChange(false),
    });
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--surface)] rounded-lg shadow-2xl p-6 w-full max-w-md z-50">
          <div className="flex items-start justify-between mb-4">
            <div>
              <Dialog.Title className="text-lg font-semibold text-[var(--ink)]">Delete subscription plan</Dialog.Title>
              <Dialog.Description className="text-[13px] text-[var(--ink-muted)] mt-1">
                This action cannot be undone.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button className="text-[var(--ink-subtle)] hover:text-[var(--ink)] transition-colors" disabled={deleteMutation.isPending}>
                <X size={20} />
              </button>
            </Dialog.Close>
          </div>

          <div className="mb-4">
            <p className="text-[13px] text-[var(--ink-muted)]">
              Are you sure you want to delete the <span className="font-medium text-[var(--ink)]">{plan.tier}</span> plan with capital of ₹{plan.capital.toLocaleString()}?
            </p>
          </div>

          {deleteMutation.error && (
            <div className="mb-4">
              <AdminError message={deleteMutation.error.message} />
            </div>
          )}

          <div className="flex gap-2">
            <Button type="button" variant="secondary" size="md" onClick={() => onOpenChange(false)} disabled={deleteMutation.isPending} className="flex-1">
              Cancel
            </Button>
            <Button type="button" variant="primary" size="md" onClick={handleDelete} disabled={deleteMutation.isPending} className="flex-1 bg-red-500 hover:bg-red-600">
              {deleteMutation.isPending ? <LoaderCircle size={16} className="animate-spin" /> : "Delete plan"}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function SubscriptionPlansPage() {
  const { data, isLoading, isError } = useSubscriptionPlans();
  const [createOpen, setCreateOpen] = useState(false);
  const [editPlan, setEditPlan] = useState<AdminSubscriptionPlan | null>(null);
  const [deletePlan, setDeletePlan] = useState<AdminSubscriptionPlan | null>(null);

  return (
    <div>
      <AdminPageTitle eyebrow="SUBSCRIPTION MANAGEMENT" title="Manage subscription plans">
        Create, edit, and delete subscription plans. Changes are reflected immediately for users.
      </AdminPageTitle>

      <SectionCard>
        <SectionCardHeader 
          eyebrow="PLAN CATALOG" 
          title="Subscription plans"
          action={
            <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus size={14} /> Create plan
            </Button>
          }
        />

        {isLoading ? (
          <AdminLoadingRows />
        ) : isError ? (
          <div className="p-5">
            <AdminError message="Subscription plans could not be loaded." />
          </div>
        ) : !data?.length ? (
          <AdminEmpty message="No subscription plans exist. Create one to get started." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[var(--surface-raised)] border-y border-[var(--line)]">
                <tr>
                  <th className="px-5 py-3 text-left text-[11px] font-semibold text-[var(--ink-subtle)] uppercase tracking-wide">Tier</th>
                  <th className="px-5 py-3 text-left text-[11px] font-semibold text-[var(--ink-subtle)] uppercase tracking-wide">Capital</th>
                  <th className="px-5 py-3 text-left text-[11px] font-semibold text-[var(--ink-subtle)] uppercase tracking-wide">Nifty</th>
                  <th className="px-5 py-3 text-left text-[11px] font-semibold text-[var(--ink-subtle)] uppercase tracking-wide">Sensex</th>
                  <th className="px-5 py-3 text-left text-[11px] font-semibold text-[var(--ink-subtle)] uppercase tracking-wide">Bank Nifty</th>
                  <th className="px-5 py-3 text-left text-[11px] font-semibold text-[var(--ink-subtle)] uppercase tracking-wide">Status</th>
                  <th className="px-5 py-3 text-right text-[11px] font-semibold text-[var(--ink-subtle)] uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {data.map((plan) => (
                  <tr key={plan.id} className="hover:bg-[var(--surface-raised)]/50 transition-colors">
                    <td className="px-5 py-4">
                      <span className="inline-flex items-center px-2 py-1 rounded text-[11px] font-medium bg-blue-500/10 text-blue-500">
                        {plan.tier}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-[13px] font-medium text-[var(--ink)]">₹{plan.capital.toLocaleString()}</td>
                    <td className="px-5 py-4 text-[13px] text-[var(--ink-muted)]">{plan.nifty_lots} lots</td>
                    <td className="px-5 py-4 text-[13px] text-[var(--ink-muted)]">{plan.sensex_lots} lots</td>
                    <td className="px-5 py-4 text-[13px] text-[var(--ink-muted)]">{plan.bank_nifty_lots} lots</td>
                    <td className="px-5 py-4">
                      {plan.is_active ? (
                        <span className="inline-flex items-center px-2 py-1 rounded text-[11px] font-medium bg-green-500/10 text-green-500">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded text-[11px] font-medium bg-gray-500/10 text-gray-500">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setEditPlan(plan)}
                          className="p-2 text-[var(--ink-subtle)] hover:text-blue-500 hover:bg-blue-500/10 rounded transition-colors"
                          title="Edit plan"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => setDeletePlan(plan)}
                          className="p-2 text-[var(--ink-subtle)] hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
                          title="Delete plan"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <PlanDialog mode="create" open={createOpen} onOpenChange={setCreateOpen} />
      {editPlan && <PlanDialog mode="edit" plan={editPlan} open={!!editPlan} onOpenChange={(open) => !open && setEditPlan(null)} />}
      {deletePlan && <DeleteConfirmDialog plan={deletePlan} open={!!deletePlan} onOpenChange={(open) => !open && setDeletePlan(null)} />}
    </div>
  );
}
