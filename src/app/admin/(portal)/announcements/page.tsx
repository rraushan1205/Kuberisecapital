import type { Metadata } from "next";
import { AnnouncementsPage } from "@/features/admin/components/announcements-page";

export const metadata: Metadata = { title: "Announcements" };

export default function AnnouncementsRoute() {
  return <AnnouncementsPage />;
}
