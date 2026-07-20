"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle, Send } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { AdminError, AdminEmpty, AdminLoadingRows } from "@/features/admin/components/admin-data-state";
import { AdminPageTitle } from "@/features/admin/components/admin-page-title";
import { useAnnouncements, useCreateAnnouncement } from "@/features/admin/hooks/use-admin-data";
import { formatDateTime } from "@/features/admin/lib/format";

const announcementSchema = z.object({
  title: z.string().trim().min(1, "Enter a title.").max(160, "Use 160 characters or fewer."),
  message: z.string().trim().min(1, "Enter an announcement.").max(5000, "Use 5,000 characters or fewer."),
});

type AnnouncementValues = z.infer<typeof announcementSchema>;

export function AnnouncementsPage() {
  const announcements = useAnnouncements();
  const createAnnouncement = useCreateAnnouncement();
  const form = useForm<AnnouncementValues>({ resolver: zodResolver(announcementSchema), mode: "onBlur", defaultValues: { title: "", message: "" } });
  const { errors, isSubmitting } = form.formState;

  function submit(values: AnnouncementValues) {
    createAnnouncement.mutate(values, {
      onSuccess: () => form.reset(),
      onError: () => form.setError("root", { message: "The announcement could not be saved. Try again." }),
    });
  }

  return <div><AdminPageTitle eyebrow="ANNOUNCEMENTS" title="Client communication">Create administrative notices for the client portal. Published notices are retained as records.</AdminPageTitle><div className="grid items-start gap-5 xl:grid-cols-[minmax(0,0.84fr)_minmax(0,1.16fr)]"><SectionCard><SectionCardHeader eyebrow="NEW ANNOUNCEMENT" title="Create notice" /><form className="space-y-4 p-5" noValidate onSubmit={form.handleSubmit(submit)}><label className="block"><span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">Title</span><input className="auth-input" aria-invalid={!!errors.title} placeholder="Notice title" {...form.register("title")} />{errors.title && <span className="mt-1.5 block text-[11px] text-[var(--danger)]">{errors.title.message}</span>}</label><label className="block"><span className="mb-1.5 block text-[12px] font-medium text-[var(--ink)]">Message</span><textarea rows={7} className="auth-input h-auto min-h-36 resize-y py-3" aria-invalid={!!errors.message} placeholder="Write the administrative notice…" {...form.register("message")} />{errors.message && <span className="mt-1.5 block text-[11px] text-[var(--danger)]">{errors.message.message}</span>}</label>{errors.root?.message && <p role="alert" className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2.5 text-[12px] text-[var(--danger)]">{errors.root.message}</p>}<Button type="submit" variant="primary" className="w-full" disabled={isSubmitting || createAnnouncement.isPending}>{isSubmitting || createAnnouncement.isPending ? <><LoaderCircle size={15} className="animate-spin" />Saving</> : <><Send size={15} />Publish announcement</>}</Button></form></SectionCard><SectionCard><SectionCardHeader eyebrow="PUBLISHED RECORD" title="Announcements" />{announcements.isLoading ? <AdminLoadingRows rows={5} /> : announcements.isError ? <div className="p-5"><AdminError message="Announcements could not be loaded." /></div> : !announcements.data?.length ? <AdminEmpty message="No announcements have been published." /> : <div className="divide-y divide-[var(--line)]">{announcements.data.map((announcement) => <article key={announcement.id} className="px-5 py-4"><div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1"><h2 className="text-[13px] font-semibold text-[var(--ink)]">{announcement.title}</h2><time className="font-mono text-[10px] text-[var(--ink-subtle)]">{formatDateTime(announcement.created_at)}</time></div><p className="mt-2 whitespace-pre-wrap text-[12px] leading-5 text-[var(--ink-muted)]">{announcement.message}</p></article>)}</div>}</SectionCard></div></div>;
}
