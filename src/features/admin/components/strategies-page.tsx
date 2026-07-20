"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, FileCode2, LoaderCircle, Play, ShieldAlert, Square, Upload, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { useAdminStrategies, useForceSquareOff, useStrategyCommand, useUploadStrategy } from "@/features/admin/hooks/use-admin-data";
import { formatDateTime } from "@/features/admin/lib/format";

const uploadSchema = z.object({
  name: z.string().trim().min(1, "Enter a strategy name.").max(160, "Use 160 characters or fewer."),
});

type UploadValues = z.infer<typeof uploadSchema>;

function UploadStrategyDialog({ disabled }: { disabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [script, setScript] = useState<File | null>(null);
  const upload = useUploadStrategy();
  const form = useForm<UploadValues>({
    resolver: zodResolver(uploadSchema),
    mode: "onBlur",
    defaultValues: { name: "" },
  });

  function close(force = false) {
    if (upload.isPending && !force) return;
    setOpen(false);
    setScript(null);
    form.reset();
  }

  function submit(values: UploadValues) {
    if (!script) {
      form.setError("root", { message: "Choose the Python file to upload." });
      return;
    }
    if (!script.name.toLowerCase().endsWith(".py")) {
      form.setError("root", { message: "Only .py Python files can be uploaded." });
      return;
    }
    if (script.size > 1_048_576) {
      form.setError("root", { message: "Strategy files are limited to 1 MB." });
      return;
    }
    upload.mutate({ name: values.name.trim(), script }, {
      onSuccess: () => close(true),
      onError: () => form.setError("root", { message: "The strategy could not be uploaded. Check the file and try again." }),
    });
  }

  return <Dialog.Root open={open} onOpenChange={(nextOpen) => !upload.isPending && setOpen(nextOpen)}>
    <Button variant="primary" size="sm" onClick={() => setOpen(true)} disabled={disabled}><Upload size={15} />Upload strategy</Button>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-[#071015]/45" />
      <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5 shadow-2xl outline-none sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div><p className="mb-2 font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--danger)]">ADMIN-ONLY UPLOAD</p><Dialog.Title className="text-[18px] font-semibold tracking-[-0.035em] text-[var(--ink)]">Add a Python strategy</Dialog.Title><Dialog.Description className="mt-2 max-w-md text-[12px] leading-5 text-[var(--ink-muted)]">The file is stored for the trading engine. It is not opened or editable in this portal or the client marketplace.</Dialog.Description></div>
          <Button size="icon" variant="quiet" onClick={() => close()} aria-label="Close upload dialog"><X size={17} /></Button>
        </div>
        <form className="mt-6 space-y-4" onSubmit={form.handleSubmit(submit)} noValidate>
          <label className="block"><span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">Strategy name</span><input className="auth-input" placeholder="e.g. Intraday momentum" aria-invalid={!!form.formState.errors.name} {...form.register("name")} />{form.formState.errors.name && <span className="mt-1.5 block text-[11px] text-[var(--danger)]">{form.formState.errors.name.message}</span>}</label>
          <label className="block"><span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">Python file</span><input type="file" accept=".py,text/x-python" className="block w-full cursor-pointer rounded-lg border border-dashed border-[var(--line-strong)] bg-[var(--panel-raised)] px-3 py-2.5 text-[12px] text-[var(--ink-muted)] file:mr-3 file:rounded-md file:border-0 file:bg-[var(--accent-soft)] file:px-2.5 file:py-1.5 file:text-[11px] file:font-medium file:text-[var(--accent)]" onChange={(event) => { setScript(event.target.files?.[0] || null); form.clearErrors("root"); }} />{script && <span className="mt-1.5 block truncate font-mono text-[10px] text-[var(--ink-muted)]">{script.name} · {(script.size / 1024).toFixed(1)} KB</span>}</label>
          {form.formState.errors.root?.message && <p role="alert" className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2.5 text-[12px] text-[var(--danger)]">{form.formState.errors.root.message}</p>}
          <div className="flex justify-end gap-2 border-t border-[var(--line)] pt-4"><Button variant="secondary" onClick={() => close()} disabled={upload.isPending}>Cancel</Button><Button type="submit" variant="primary" disabled={upload.isPending}>{upload.isPending ? <><LoaderCircle size={15} className="animate-spin" />Uploading</> : <><Upload size={15} />Upload file</>}</Button></div>
        </form>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}

function ForceSquareOffDialog() {
  const [open, setOpen] = useState(false);
  const forceSquareOff = useForceSquareOff();
  return <Dialog.Root open={open} onOpenChange={(nextOpen) => !forceSquareOff.isPending && setOpen(nextOpen)}>
    <Button variant="danger" size="sm" onClick={() => setOpen(true)}><AlertTriangle size={15} />Force square off</Button>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-[#071015]/45" />
      <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-[480px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5 shadow-2xl outline-none sm:p-6">
        <div className="flex items-start gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--danger-soft)] text-[var(--danger)]"><ShieldAlert size={18} /></span><div><p className="mb-2 font-mono text-[10px] font-medium tracking-[0.12em] text-[var(--danger)]">EXECUTION CONTROL</p><Dialog.Title className="text-[18px] font-semibold tracking-[-0.035em] text-[var(--ink)]">Force square off all positions?</Dialog.Title><Dialog.Description className="mt-2 text-[12px] leading-5 text-[var(--ink-muted)]">This sends a force square off command to the configured trading engine. It is logged only after the engine accepts the command.</Dialog.Description></div></div>
        {forceSquareOff.error && <div className="mt-4"><AdminError message="The trading engine did not accept the square off command." /></div>}
        <div className="mt-6 flex justify-end gap-2"><Button variant="secondary" onClick={() => setOpen(false)} disabled={forceSquareOff.isPending}>Cancel</Button><Button variant="danger" onClick={() => forceSquareOff.mutate(undefined, { onSuccess: () => setOpen(false) })} disabled={forceSquareOff.isPending}>{forceSquareOff.isPending ? <><LoaderCircle size={15} className="animate-spin" />Sending</> : <><AlertTriangle size={15} />Confirm square off</>}</Button></div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}

export function StrategiesPage() {
  const { data, isLoading, isError } = useAdminStrategies();
  const command = useStrategyCommand();
  const [activeStrategyId, setActiveStrategyId] = useState<string | null>(null);
  const atCapacity = (data?.length || 0) >= 3;

  function sendCommand(strategyId: string, commandName: "start" | "stop") {
    setActiveStrategyId(strategyId);
    command.mutate({ strategyId, command: commandName }, { onSettled: () => setActiveStrategyId(null) });
  }

  return <div><AdminPageTitle eyebrow="STRATEGY UPLOAD & CONTROL" title="Approved strategy files">Only the Super Admin can upload Python files. Client users receive read-only strategy records and cannot view or edit uploaded source.</AdminPageTitle>{command.error && <div className="mb-4"><AdminError message="The trading engine did not accept the strategy command." /></div>}<SectionCard><SectionCardHeader eyebrow="TRADING ENGINE INVENTORY" title="Strategies" action={<div className="flex items-center gap-2"><ForceSquareOffDialog /><UploadStrategyDialog disabled={isLoading || atCapacity} /></div>} />{isLoading ? <AdminLoadingRows rows={3} /> : isError ? <div className="p-5"><AdminError message="Strategy records could not be loaded." /></div> : !data?.length ? <AdminEmpty message="No strategy files have been uploaded." /> : <div className="divide-y divide-[var(--line)]">{data.map((strategy) => { const isRunning = strategy.status === "RUNNING"; const isPending = activeStrategyId === strategy.id; return <article key={strategy.id} className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"><div className="min-w-0"><div className="flex items-center gap-2.5"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]"><FileCode2 size={16} /></span><div className="min-w-0"><h2 className="truncate text-[13px] font-semibold text-[var(--ink)]">{strategy.name}</h2><p className="mt-0.5 truncate font-mono text-[10px] text-[var(--ink-muted)]">{strategy.script_filename}</p></div></div><p className="mt-2 text-[11px] text-[var(--ink-subtle)]">Uploaded {formatDateTime(strategy.created_at)} · source remains storage-only</p></div><div className="flex items-center gap-2"><span className={isRunning ? "rounded-md border border-[var(--positive)] bg-[var(--positive-soft)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--positive)]" : "rounded-md border border-[var(--line)] px-2 py-1 font-mono text-[9px] tracking-[0.08em] text-[var(--ink-muted)]"}>{strategy.status}</span><Button variant={isRunning ? "secondary" : "primary"} size="sm" onClick={() => sendCommand(strategy.id, isRunning ? "stop" : "start")} disabled={command.isPending}>{isPending ? <LoaderCircle size={14} className="animate-spin" /> : isRunning ? <Square size={14} /> : <Play size={14} />}{isRunning ? "Stop" : "Start"}</Button></div></article>; })}</div>}</SectionCard><p className="mt-3 text-[11px] leading-5 text-[var(--ink-subtle)]">The platform permits a maximum of three strategy files. At capacity, uploading is disabled.</p></div>;
}
