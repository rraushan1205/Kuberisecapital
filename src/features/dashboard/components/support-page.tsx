import { CircleHelp, ShieldAlert } from "lucide-react";
import { DataUnavailable } from "@/components/ui/data-state";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { WorkspacePageTitle } from "@/features/dashboard/components/workspace-page-title";

export function SupportPage() {
  return (
    <div>
      <WorkspacePageTitle eyebrow="SUPPORT" title="Account assistance">Support requests are handled through the channel configured for your organization.</WorkspacePageTitle>
      <SectionCard>
        <SectionCardHeader eyebrow="SUPPORT CHANNEL" title="Request assistance" />
        <DataUnavailable message="No support channel has been configured for this account." />
      </SectionCard>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <InfoCard icon={<ShieldAlert size={17} />} title="Access & subscription" body="Contact your administrator for approval, account status, or subscription-related questions." />
        <InfoCard icon={<CircleHelp size={17} />} title="Strategy & broker help" body="For published strategy or broker connection issues, share the relevant account context with your assigned support channel." />
      </div>
    </div>
  );
}

function InfoCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return <SectionCard className="p-5"><div className="mb-6 text-[var(--accent)]">{icon}</div><h2 className="text-[13px] font-semibold text-[var(--ink)]">{title}</h2><p className="mt-2 text-[12px] leading-5 text-[var(--ink-muted)]">{body}</p></SectionCard>;
}
