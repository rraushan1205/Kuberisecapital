"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthShell } from "@/components/auth-shell";
import { AuthHeading } from "@/components/auth-primitives";
import { setSession } from "@/lib/session-storage";

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Extract tokens from URL query parameters
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");
    const userId = searchParams.get("user_id");
    const email = searchParams.get("email");
    const accountStatus = searchParams.get("account_status");

    // Check for error parameter
    const errorParam = searchParams.get("error");
    if (errorParam) {
      let errorMessage = "Unable to authenticate with Fyers.";
      
      if (errorParam === "no_account") {
        errorMessage = "No Kuberise Capital account found. Please register with email first, then connect your broker.";
      } else if (errorParam === "broker_auth_failed") {
        errorMessage = "Fyers authentication failed. Please try again.";
      } else if (errorParam === "invalid_state") {
        errorMessage = "Invalid authentication state. Please try again.";
      }
      
      setError(errorMessage);
      
      // Redirect back to login after showing error
      setTimeout(() => {
        router.replace("/login");
      }, 3000);
      return;
    }

    // Validate required parameters
    if (!accessToken || !refreshToken || !userId || !email) {
      setError("Invalid authentication response. Please try again.");
      setTimeout(() => {
        router.replace("/login");
      }, 3000);
      return;
    }

    // Store session tokens
    try {
      setSession({
        access_token: accessToken,
        refresh_token: refreshToken,
      });

      // Handle account status redirects
      if (accountStatus === "pending") {
        router.replace(`/pending-approval?email=${encodeURIComponent(email)}`);
        return;
      }

      if (accountStatus === "rejected") {
        router.replace(`/account-rejected?email=${encodeURIComponent(email)}`);
        return;
      }

      // Success - redirect to dashboard
      router.replace("/dashboard");
    } catch (err) {
      setError("Failed to establish session. Please try again.");
      setTimeout(() => {
        router.replace("/login");
      }, 3000);
    }
  }, [searchParams, router]);

  return (
    <AuthShell>
      <div className="text-center">
        <AuthHeading eyebrow="AUTHENTICATION" title={error ? "Authentication Failed" : "Completing sign in..."}>
          {error ? error : "Please wait while we sign you in with Fyers."}
        </AuthHeading>
        
        {error ? (
          <div className="mt-6 rounded-lg border border-[var(--danger)] bg-[var(--danger)]/5 px-4 py-3 text-sm text-[var(--danger)]">
            {error}
            <div className="mt-2 text-xs">Redirecting to login page...</div>
          </div>
        ) : (
          <div className="mt-6 flex items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--primary)]"></div>
          </div>
        )}
      </div>
    </AuthShell>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={
      <AuthShell>
        <div className="text-center">
          <AuthHeading eyebrow="AUTHENTICATION" title="Loading...">
            Please wait while we process your authentication.
          </AuthHeading>
          <div className="mt-6 flex items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--primary)]"></div>
          </div>
        </div>
      </AuthShell>
    }>
      <OAuthCallbackContent />
    </Suspense>
  );
}
