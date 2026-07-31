import type { Metadata } from "next";
import { SubscriptionPlansPage } from "@/features/admin/components/subscription-plans-page";

export const metadata: Metadata = { title: "Subscription plans" };

export default function SubscriptionsRoute() {
  return <SubscriptionPlansPage />;
}
