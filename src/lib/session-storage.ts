/**
 * Tab-scoped session token storage.
 *
 * Tokens live in `sessionStorage` (never `localStorage`), so they are scoped to a
 * single tab: closing the tab destroys them, and a fresh tab has no session and is
 * redirected to login. This is the mechanism that gives per-tab session death.
 *
 * Security note: unlike HTTP-only cookies, `sessionStorage` tokens are readable by
 * page JavaScript, so a successful XSS could exfiltrate them. This is the inherent
 * trade-off of per-tab sessions. Mitigations: access tokens stay short-lived and
 * the refresh token is rotated server-side on every use.
 */

export type SessionKind = "user" | "admin";

const ACCESS_KEY: Record<SessionKind, string> = {
  user: "kuberise_access",
  admin: "kuberise_admin_access",
};

const REFRESH_KEY: Record<SessionKind, string> = {
  user: "kuberise_refresh",
  admin: "kuberise_admin_refresh",
};

export function getAccessToken(kind: SessionKind = "user"): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(ACCESS_KEY[kind]);
}

export function getRefreshToken(kind: SessionKind = "user"): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(REFRESH_KEY[kind]);
}

export function setSession(tokens: { access_token: string; refresh_token: string }, kind: SessionKind = "user"): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(ACCESS_KEY[kind], tokens.access_token);
  window.sessionStorage.setItem(REFRESH_KEY[kind], tokens.refresh_token);
}

export function clearSession(kind: SessionKind = "user"): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(ACCESS_KEY[kind]);
  window.sessionStorage.removeItem(REFRESH_KEY[kind]);
}

export function authHeader(kind: SessionKind = "user"): Record<string, string> {
  const token = getAccessToken(kind);
  return token ? { Authorization: `Bearer ${token}` } : {};
}
