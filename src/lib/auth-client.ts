import { clearSession, getRefreshToken, setSession } from "@/lib/session-storage";

export type AccountStatus = "APPROVED" | "PENDING" | "REJECTED";

export interface RegisterResponse {
  message: string;
  email: string;
}

interface ClientSessionPayload {
  user_id: string;
  email: string;
  account_status: string;
  access_token: string;
  refresh_token: string;
}

const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
let refreshInFlight: Promise<AccountStatus> | null = null;

export async function refreshClientSession(): Promise<AccountStatus> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) throw new Error("Your session could not be refreshed.");
      const response = await fetch(`${apiBaseUrl}/api/v1/client/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) throw new Error("Your session could not be refreshed.");
      const data = await response.json() as ClientSessionPayload;
      setSession({ access_token: data.access_token, refresh_token: data.refresh_token });
      return data.account_status as AccountStatus;
    })().finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

export async function login(email: string, password: string): Promise<{ status?: AccountStatus; requires2FA?: boolean; temp2faToken?: string }> {
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

  const data = await response.json() as ClientSessionPayload;
  if (data.requires_2fa && data.temp_2fa_token) {
    return { requires2FA: true, temp2faToken: data.temp_2fa_token };
  }

  setSession({ access_token: data.access_token!, refresh_token: data.refresh_token! });
  return { status: data.account_status as AccountStatus };
}

export async function verify2FALogin(temp2faToken: string, totpCode: string): Promise<AccountStatus> {
  const response = await fetch(`${apiBaseUrl}/api/v1/client/auth/verify-2fa`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ temp_2fa_token: temp2faToken, totp_code: totpCode }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || "Invalid Google Authenticator code.");
  }

  const data = await response.json() as ClientSessionPayload;
  setSession({ access_token: data.access_token!, refresh_token: data.refresh_token! });
  return data.account_status as AccountStatus;
}

export async function registerUser(
  email: string,
  password: string,
  fullName: string,
  invitationCode: string,
): Promise<RegisterResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      invitation_code: invitationCode,
    }),
  });

  if (response.status === 409) {
    throw new Error("An account with this email already exists.");
  }
  if (!response.ok) {
    const errorData = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(errorData?.detail || "Registration failed. Please try again.");
  }

  return await response.json() as RegisterResponse;
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  try {
    if (refreshToken) {
      await fetch(`${apiBaseUrl}/api/v1/client/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    }
  } finally {
    clearSession();
  }
}
