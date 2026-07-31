"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getAccessToken, type SessionKind } from "@/lib/session-storage";

const LOGIN_ROUTE: Record<SessionKind, string> = {
  user: "/login",
  admin: "/admin/login",
};

/**
 * Client-side route guard. The old Next.js middleware could only read cookies,
 * but sessions now live in tab-scoped `sessionStorage`, so protected pages must
 * check for the access token in the browser. When the token is missing (fresh
 * tab, closed tab, expired-and-unrefreshable session) the guard redirects to the
 * matching login page, preserving the original path in `?next=`.
 *
 * Renders nothing until the check settles so an unauthenticated visitor never
 * sees a flash of the protected shell.
 */
export function SessionGuard({ kind, children }: { kind: SessionKind; children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    if (getAccessToken(kind)) {
      setAuthed(true);
      return;
    }
    const loginPath = LOGIN_ROUTE[kind];
    const next = pathname && pathname !== "/" ? `?next=${encodeURIComponent(pathname)}` : "";
    router.replace(`${loginPath}${next}`);
  }, [kind, pathname, router]);

  if (authed !== true) return null;

  return <>{children}</>;
}
