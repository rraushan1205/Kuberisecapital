import type { Metadata } from "next";
import { SubscriptionsPage } from "@/features/admin/components/subscriptions-page";

export const metadata: Metadata = { title: "Subscription approval" };

export default function SubscriptionsRoute() {
  return <SubscriptionsPage />;
}
