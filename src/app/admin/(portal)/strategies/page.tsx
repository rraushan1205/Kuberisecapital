import type { Metadata } from "next";
import { StrategiesPage } from "@/features/admin/components/strategies-page";

export const metadata: Metadata = { title: "Strategies" };

export default function StrategiesRoute() {
  return <StrategiesPage />;
}
