export type AccountStatus = "approved" | "pending" | "rejected";

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export async function login(email: string, password: string): Promise<AccountStatus> {
  const response = await fetch(`${apiBaseUrl}/api/v1/client/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (response.status === 401) {
    throw new Error("Invalid email or password.");
  }
  if (response.status === 403) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || "Access denied.");
  }
  if (!response.ok) {
    throw new Error("Unable to sign in right now.");
  }

  const data = await response.json() as { account_status: string };
  return data.account_status as AccountStatus;
}

export async function logout(): Promise<void> {
  await fetch(`${apiBaseUrl}/api/v1/client/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
}
