import type { Metadata } from "next";
import { MyStrategiesPage } from "@/features/dashboard/components/my-strategies-page";

export const metadata: Metadata = { title: "My Strategies" };

export default function MarketplaceRoute() {
  return <MyStrategiesPage />;
}
