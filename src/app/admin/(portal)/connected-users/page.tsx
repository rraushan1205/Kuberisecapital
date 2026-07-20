import type { Metadata } from "next";
import { ConnectedUsersPage } from "@/features/admin/components/connected-users-page";

export const metadata: Metadata = { title: "Connected users" };

export default function ConnectedUsersRoute() {
  return <ConnectedUsersPage />;
}
