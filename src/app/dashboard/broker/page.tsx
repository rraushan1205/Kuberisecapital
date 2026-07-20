import type { Metadata } from "next";
import { BrokerPage } from "@/features/dashboard/components/broker-page";

export const metadata: Metadata = { title: "Broker" };

export default function BrokerRoute() {
  return <BrokerPage />;
}
