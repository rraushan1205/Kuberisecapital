import type { Metadata } from "next";
import { PendingRegistrationsPage } from "@/features/admin/components/pending-registrations-page";

export const metadata: Metadata = { title: "Pending registrations" };

export default function PendingRegistrationsRoute() {
  return <PendingRegistrationsPage />;
}
