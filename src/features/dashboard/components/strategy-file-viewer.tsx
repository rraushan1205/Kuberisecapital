"use client";

import { useQuery } from "@tanstack/react-query";
import { getStrategyFileView, getStrategyDownloadUrl } from "@/features/dashboard/api/dashboard-api";
import { WorkspacePageTitle } from "./workspace-page-title";
import { Button } from "@/components/ui/button";
import { Download, ArrowLeft, FileCode } from "lucide-react";
import Link from "next/link";

export function StrategyFileViewer({ strategyId }: { strategyId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["strategy-file-view", strategyId],
    queryFn: () => getStrategyFileView(strategyId),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <WorkspacePageTitle
          title="Strategy File Viewer"
          description="Loading file content..."
        />
        <div className="flex items-center justify-center h-96">
          <div className="text-muted-foreground">Loading strategy file...</div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <WorkspacePageTitle
          title="Strategy File Viewer"
          description="Unable to load file content"
        />
        <div className="flex flex-col items-center justify-center h-96 space-y-4">
          <FileCode className="h-12 w-12 text-muted-foreground" />
          <div className="text-muted-foreground">
            {error instanceof Error ? error.message : "Failed to load strategy file"}
          </div>
          <Button asChild variant="outline">
            <Link href="/dashboard/marketplace">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Marketplace
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <WorkspacePageTitle
        title="Strategy File Viewer"
        description={data.message || "View and download strategy files"}
      />

      {/* File Header */}
      <div className="bg-card border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <FileCode className="h-5 w-5 text-muted-foreground" />
            <div>
              <h3 className="font-semibold text-foreground">{data.filename}</h3>
              <p className="text-sm text-muted-foreground">
                {data.readonly ? "Read-only • Admin-managed file" : "Editable file"}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/marketplace">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Link>
            </Button>
            <Button asChild variant="default" size="sm">
              <a
                href={getStrategyDownloadUrl(strategyId)}
                download={data.filename}
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </a>
            </Button>
          </div>
        </div>

        {/* File Content */}
        <div className="bg-muted/30 border rounded-md p-4 overflow-x-auto">
          <pre className="text-sm text-foreground font-mono whitespace-pre-wrap break-words">
            <code>{data.content}</code>
          </pre>
        </div>

        {/* Footer Info */}
        {data.readonly && (
          <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-md">
            <p className="text-sm text-amber-600 dark:text-amber-400">
              ⚠️ This file is managed by administrators and cannot be edited. You can download it for local use.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
