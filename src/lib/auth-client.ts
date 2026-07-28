export type AccountStatus = "APPROVED" | "PENDING" | "REJECTED";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string | null;
    role: string;
    account_status: string;
    email_verified: boolean;
  };
}

export interface RegisterResponse {
  message: string;
  email: string;
}

export interface AccountStatusResponse {
  email: string;
  account_status: string;
  message: string;
}

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

export async function registerUser(
  email: string,
  password: string,
  fullName: string,
  phoneNumber?: string,
  invitationCode?: string
): Promise<RegisterResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/register`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      phone_number: phoneNumber,
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
  await fetch(`${apiBaseUrl}/api/v1/client/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
}
