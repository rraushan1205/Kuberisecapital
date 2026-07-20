export type AccountStatus = "approved" | "pending" | "rejected";

/**
 * Temporary UI contract. Connect these functions to the application auth API;
 * no credentials are persisted in the browser by this interface.
 */
export async function resolveAccountStatus(email: string): Promise<AccountStatus> {
  await new Promise((resolve) => window.setTimeout(resolve, 550));

  // These two addresses make status states easy to exercise during integration.
  // Replace this adapter with the identity provider response in production.
  if (email.toLowerCase().startsWith("pending@")) return "pending";
  if (email.toLowerCase().startsWith("rejected@")) return "rejected";
  return "approved";
}

export function establishSession() {
  document.cookie = "stratum_session=1; path=/; max-age=28800; samesite=lax";
}
