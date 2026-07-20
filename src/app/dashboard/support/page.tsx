import type { Metadata } from "next";
import { SupportPage } from "@/features/dashboard/components/support-page";

export const metadata: Metadata = { title: "Support" };

export default function SupportRoute() {
  return <SupportPage />;
}
