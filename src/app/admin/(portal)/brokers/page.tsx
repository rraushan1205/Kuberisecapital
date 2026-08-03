import type { Metadata } from "next";
import { BrokersPage } from "@/features/admin/components/brokers-page";

export const metadata: Metadata = { title: "Broker accounts" };

export default function AdminBrokersRoute() {
  return <BrokersPage />;
}
