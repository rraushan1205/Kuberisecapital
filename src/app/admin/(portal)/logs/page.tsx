import type { Metadata } from "next";
import { ExecutionLogsPage } from "@/features/admin/components/execution-logs-page";

export const metadata: Metadata = { title: "Execution logs" };

export default function ExecutionLogsRoute() {
  return <ExecutionLogsPage />;
}
