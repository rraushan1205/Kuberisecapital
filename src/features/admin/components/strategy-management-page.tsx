"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, Code2, FileCode2, LoaderCircle, Plus, Trash2, Users, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { adminApi } from "@/features/admin/api/admin-api";
import { formatDateTime } from "@/features/admin/lib/format";
import type { StrategyDefinition, UserStrategyAssignment, AdminUser } from "@/features/admin/types";

// ========== SCHEMAS ==========

const strategyDefSchema = z.object({
  name: z.string().trim().min(1, "Strategy name required").max(100, "Max 100 characters"),
  description: z.string().trim().min(1, "Description required").max(500, "Max 500 characters"),
  code: z.string().trim().min(1, "Strategy code required"),
});

const assignmentSchema = z.object({
  user_id: z.string().min(1, "Select a user"),
  strategy_def_id: z.number().min(1, "Select a strategy"),
  config: z.string().optional(),
});

type StrategyDefValues = z.infer<typeof strategyDefSchema>;
type AssignmentValues = z.infer<typeof assignmentSchema>;

// ========== CREATE STRATEGY DEFINITION DIALOG ==========

function CreateStrategyDialog() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const form = useForm<StrategyDefValues>({
    resolver: zodResolver(strategyDefSchema),
    defaultValues: { name: "", description: "", code: "" },
  });

  const createMutation = useMutation({
    mutationFn: (data: StrategyDefValues) => adminApi.createStrategyDefinition(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategyDefinitions"] });
      setOpen(false);
      form.reset();
    },
    onError: () => {
      form.setError("root", { message: "Failed to create strategy. Check code for errors." });
    },
  });

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => !createMutation.isPending && setOpen(nextOpen)}>
      <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
        <Plus size={15} />
        Create strategy
      </Button>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[#071015]/45" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-[800px] max-h-[90vh] overflow-y-auto -translate-x-1/2 -translate-y-1/2 rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5 shadow-2xl outline-none sm:p-6">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <p className="mb-2 font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--accent)]">
                STRATEGY DEFINITION
              </p>
              <Dialog.Title className="text-[18px] font-semibold tracking-[-0.035em] text-[var(--ink)]">
                Create new strategy
              </Dialog.Title>
              <Dialog.Description className="mt-2 text-[12px] leading-5 text-[var(--ink-muted)]">
                Define a new trading strategy with Python code. The code will be validated and can be assigned to users.
              </Dialog.Description>
            </div>
            <Button size="icon" variant="quiet" onClick={() => setOpen(false)} aria-label="Close">
              <X size={17} />
            </Button>
          </div>
          <form className="space-y-4" onSubmit={form.handleSubmit((data) => createMutation.mutate(data))} noValidate>
            <label className="block">
              <span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">Strategy name</span>
              <input
                className="auth-input"
                placeholder="e.g., SENSEX EMA Crossover"
                aria-invalid={!!form.formState.errors.name}
                {...form.register("name")}
              />
              {form.formState.errors.name && (
                <span className="mt-1.5 block text-[11px] text-[var(--danger)]">
                  {form.formState.errors.name.message}
                </span>
              )}
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">Description</span>
              <textarea
                className="auth-input min-h-[80px] resize-y"
                placeholder="Describe the strategy logic and parameters..."
                aria-invalid={!!form.formState.errors.description}
                {...form.register("description")}
              />
              {form.formState.errors.description && (
                <span className="mt-1.5 block text-[11px] text-[var(--danger)]">
                  {form.formState.errors.description.message}
                </span>
              )}
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">
                Python code <span className="text-[var(--ink-muted)]">(must include check_for_signal function)</span>
              </span>
              <textarea
                className="auth-input min-h-[300px] resize-y font-mono text-[11px]"
                placeholder={`async def check_for_signal(index_df, state, config, adapter, token):\n    # Your strategy logic here\n    return None`}
                aria-invalid={!!form.formState.errors.code}
                {...form.register("code")}
              />
              {form.formState.errors.code && (
                <span className="mt-1.5 block text-[11px] text-[var(--danger)]">
                  {form.formState.errors.code.message}
                </span>
              )}
            </label>
            {form.formState.errors.root?.message && (
              <p role="alert" className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2.5 text-[12px] text-[var(--danger)]">
                {form.formState.errors.root.message}
              </p>
            )}
            <div className="flex justify-end gap-2 border-t border-[var(--line)] pt-4">
              <Button variant="secondary" onClick={() => setOpen(false)} disabled={createMutation.isPending}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={createMutation.isPending}>
                {createMutation.isPending ? (
                  <>
                    <LoaderCircle size={15} className="animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus size={15} />
                    Create strategy
                  </>
                )}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ========== STRATEGY DEFINITIONS TAB ==========

function StrategyDefinitionsTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["strategyDefinitions"],
    queryFn: () => adminApi.getStrategyDefinitions(),
  });

  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteStrategyDefinition(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategyDefinitions"] });
      queryClient.invalidateQueries({ queryKey: ["strategyAssignments"] });
    },
  });

  return (
    <div className="space-y-4">
      <SectionCard>
        <SectionCardHeader
          eyebrow="STRATEGY LIBRARY"
          title="Strategy definitions"
          action={<CreateStrategyDialog />}
        />
        {isLoading ? (
          <AdminLoadingRows rows={3} />
        ) : isError ? (
          <div className="p-5">
            <AdminError message="Failed to load strategy definitions." />
          </div>
        ) : !data?.length ? (
          <AdminEmpty message="No strategy definitions created yet." />
        ) : (
          <div className="divide-y divide-[var(--line)]">
            {data.map((strategy) => (
              <article key={strategy.id} className="flex items-start justify-between gap-4 px-5 py-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2.5">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
                      <FileCode2 size={16} />
                    </span>
                    <div className="min-w-0">
                      <h2 className="truncate text-[13px] font-semibold text-[var(--ink)]">{strategy.name}</h2>
                      <p className="mt-0.5 truncate text-[11px] text-[var(--ink-muted)]">ID: {strategy.id}</p>
                    </div>
                  </div>
                  <p className="mt-2 text-[12px] leading-5 text-[var(--ink-subtle)]">{strategy.description}</p>
                  <p className="mt-2 text-[11px] text-[var(--ink-subtle)]">
                    Created {formatDateTime(strategy.created_at)}
                  </p>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => {
                    if (confirm(`Delete "${strategy.name}"? This will deactivate all user assignments.`)) {
                      deleteMutation.mutate(strategy.id);
                    }
                  }}
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending ? (
                    <LoaderCircle size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                  Delete
                </Button>
              </article>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}

// ========== ASSIGN STRATEGY DIALOG ==========

function AssignStrategyDialog() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: users } = useQuery({
    queryKey: ["adminUsers"],
    queryFn: () => adminApi.getUsers(),
  });

  const { data: strategies } = useQuery({
    queryKey: ["strategyDefinitions"],
    queryFn: () => adminApi.getStrategyDefinitions(),
  });

  const form = useForm<AssignmentValues>({
    resolver: zodResolver(assignmentSchema),
    defaultValues: { user_id: "", strategy_def_id: 0, config: "" },
  });

  const assignMutation = useMutation({
    mutationFn: (data: AssignmentValues) => {
      const config = data.config ? JSON.parse(data.config) : {};
      return adminApi.createUserStrategyAssignment({
        user_id: data.user_id,
        strategy_def_id: data.strategy_def_id,
        config,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategyAssignments"] });
      setOpen(false);
      form.reset();
    },
    onError: () => {
      form.setError("root", { message: "Failed to assign strategy. User may already have this strategy." });
    },
  });

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => !assignMutation.isPending && setOpen(nextOpen)}>
      <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
        <Plus size={15} />
        Assign strategy
      </Button>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[#071015]/45" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5 shadow-2xl outline-none sm:p-6">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <p className="mb-2 font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--accent)]">
                STRATEGY ASSIGNMENT
              </p>
              <Dialog.Title className="text-[18px] font-semibold tracking-[-0.035em] text-[var(--ink)]">
                Assign strategy to user
              </Dialog.Title>
              <Dialog.Description className="mt-2 text-[12px] leading-5 text-[var(--ink-muted)]">
                Grant a user access to a strategy. They can start/stop it from their dashboard.
              </Dialog.Description>
            </div>
            <Button size="icon" variant="quiet" onClick={() => setOpen(false)} aria-label="Close">
              <X size={17} />
            </Button>
          </div>
          <form className="space-y-4" onSubmit={form.handleSubmit((data) => assignMutation.mutate(data))} noValidate>
            <label className="block">
              <span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">User</span>
              <select
                className="auth-input"
                aria-invalid={!!form.formState.errors.user_id}
                {...form.register("user_id")}
              >
                <option value="">Select a user</option>
                {users?.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.email} ({user.full_name || "No name"})
                  </option>
                ))}
              </select>
              {form.formState.errors.user_id && (
                <span className="mt-1.5 block text-[11px] text-[var(--danger)]">
                  {form.formState.errors.user_id.message}
                </span>
              )}
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">Strategy</span>
              <select
                className="auth-input"
                aria-invalid={!!form.formState.errors.strategy_def_id}
                {...form.register("strategy_def_id", { valueAsNumber: true })}
              >
                <option value={0}>Select a strategy</option>
                {strategies?.map((strategy) => (
                  <option key={strategy.id} value={strategy.id}>
                    {strategy.name}
                  </option>
                ))}
              </select>
              {form.formState.errors.strategy_def_id && (
                <span className="mt-1.5 block text-[11px] text-[var(--danger)]">
                  {form.formState.errors.strategy_def_id.message}
                </span>
              )}
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">
                Config JSON <span className="text-[var(--ink-muted)]">(optional)</span>
              </span>
              <textarea
                className="auth-input min-h-[100px] resize-y font-mono text-[11px]"
                placeholder='{"param1": 10, "param2": "value"}'
                {...form.register("config")}
              />
              <span className="mt-1 block text-[10px] text-[var(--ink-muted)]">
                Strategy-specific parameters as JSON
              </span>
            </label>
            {form.formState.errors.root?.message && (
              <p role="alert" className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2.5 text-[12px] text-[var(--danger)]">
                {form.formState.errors.root.message}
              </p>
            )}
            <div className="flex justify-end gap-2 border-t border-[var(--line)] pt-4">
              <Button variant="secondary" onClick={() => setOpen(false)} disabled={assignMutation.isPending}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={assignMutation.isPending}>
                {assignMutation.isPending ? (
                  <>
                    <LoaderCircle size={15} className="animate-spin" />
                    Assigning...
                  </>
                ) : (
                  <>
                    <Plus size={15} />
                    Assign
                  </>
                )}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ========== USER ASSIGNMENTS TAB ==========

function UserAssignmentsTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["strategyAssignments"],
    queryFn: () => adminApi.getUserStrategyAssignments(),
  });

  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteUserStrategyAssignment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategyAssignments"] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      adminApi.updateUserStrategyAssignment(id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategyAssignments"] });
    },
  });

  return (
    <div className="space-y-4">
      <SectionCard>
        <SectionCardHeader
          eyebrow="USER ACCESS"
          title="Strategy assignments"
          action={<AssignStrategyDialog />}
        />
        {isLoading ? (
          <AdminLoadingRows rows={3} />
        ) : isError ? (
          <div className="p-5">
            <AdminError message="Failed to load strategy assignments." />
          </div>
        ) : !data?.length ? (
          <AdminEmpty message="No strategies assigned to users yet." />
        ) : (
          <div className="divide-y divide-[var(--line)]">
            {data.map((assignment) => (
              <article key={assignment.id} className="flex items-start justify-between gap-4 px-5 py-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2.5">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
                      <Users size={16} />
                    </span>
                    <div className="min-w-0">
                      <h2 className="truncate text-[13px] font-semibold text-[var(--ink)]">
                        {assignment.strategy_name || `Strategy ${assignment.strategy_def_id}`}
                      </h2>
                      <p className="mt-0.5 truncate text-[11px] text-[var(--ink-muted)]">
                        {assignment.user_email || assignment.user_id}
                      </p>
                    </div>
                  </div>
                  {assignment.error_message && (
                    <div className="mt-2 flex items-start gap-2 rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2">
                      <AlertTriangle size={14} className="mt-0.5 shrink-0 text-[var(--danger)]" />
                      <p className="text-[11px] text-[var(--danger)]">{assignment.error_message}</p>
                    </div>
                  )}
                  <p className="mt-2 text-[11px] text-[var(--ink-subtle)]">
                    Assigned {formatDateTime(assignment.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={
                      assignment.is_active
                        ? "rounded-md border border-[var(--positive)] bg-[var(--positive-soft)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--positive)]"
                        : "rounded-md border border-[var(--line)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--ink-muted)]"
                    }
                  >
                    {assignment.is_active ? "ACTIVE" : "INACTIVE"}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      toggleMutation.mutate({ id: assignment.id, is_active: !assignment.is_active })
                    }
                    disabled={toggleMutation.isPending}
                  >
                    {toggleMutation.isPending ? (
                      <LoaderCircle size={14} className="animate-spin" />
                    ) : assignment.is_active ? (
                      "Deactivate"
                    ) : (
                      "Activate"
                    )}
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => {
                      if (confirm(`Remove this assignment for ${assignment.user_email}?`)) {
                        deleteMutation.mutate(assignment.id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? (
                      <LoaderCircle size={14} className="animate-spin" />
                    ) : (
                      <Trash2 size={14} />
                    )}
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}

// ========== MAIN PAGE ==========

export function StrategyManagementPage() {
  const [activeTab, setActiveTab] = useState<"definitions" | "assignments">("definitions");

  return (
    <div>
      <AdminPageTitle eyebrow="STRATEGY MANAGEMENT" title="Admin-managed strategies">
        Create strategy definitions and assign them to users. Strategies execute automatically when users start them.
      </AdminPageTitle>
      <div className="mt-4">
        <div className="flex gap-2 border-b border-[var(--line)] pb-2">
          <button
            onClick={() => setActiveTab("definitions")}
            className={`rounded-lg px-4 py-2 text-[12px] font-medium transition-colors ${
              activeTab === "definitions"
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
            }`}
          >
            <Code2 size={14} className="inline-block mr-1.5" />
            Strategy definitions
          </button>
          <button
            onClick={() => setActiveTab("assignments")}
            className={`rounded-lg px-4 py-2 text-[12px] font-medium transition-colors ${
              activeTab === "assignments"
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
            }`}
          >
            <Users size={14} className="inline-block mr-1.5" />
            User assignments
          </button>
        </div>
        <div className="mt-4">
          {activeTab === "definitions" ? <StrategyDefinitionsTab /> : <UserAssignmentsTab />}
        </div>
      </div>
    </div>
  );
}
