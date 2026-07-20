import type { Metadata } from "next";
import { MarketplacePage } from "@/features/dashboard/components/marketplace-page";

export const metadata: Metadata = { title: "Marketplace" };

export default function MarketplaceRoute() {
  return <MarketplacePage />;
}
