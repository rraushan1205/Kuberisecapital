import type { Metadata } from "next";
import { StrategyManagementPage } from "@/features/admin/components/strategy-management-page";

export const metadata: Metadata = { title: "Strategy Management" };

export default function StrategiesRoute() {
  return <StrategyManagementPage />;
}
