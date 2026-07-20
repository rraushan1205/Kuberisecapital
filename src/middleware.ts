import { NextResponse, type NextRequest } from "next/server";
import { jwtVerify } from "jose/jwt/verify";

const authRoutes = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/pending-approval",
  "/account-rejected",
  "/verify-email/success",
  "/verify-email/expired",
];

function forbidden() {
  return new NextResponse("Forbidden", { status: 403, headers: { "Content-Type": "text/plain; charset=utf-8" } });
}

async function hasValidSuperAdminSession(token: string | undefined) {
  const secret = process.env.JWT_SECRET_KEY;
  if (!token || !secret) return false;
  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(secret), { algorithms: ["HS256"] });
    return payload.role === "SUPER_ADMIN";
  } catch {
    return false;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has("stratum_session");
  const adminSession = request.cookies.get("stratum_admin_session")?.value;
  const hasValidAdminSession = await hasValidSuperAdminSession(adminSession);
  const isAuthRoute = authRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );

  if (pathname.startsWith("/admin")) {
    if (pathname === "/admin/login") {
      if (hasSession && !hasValidAdminSession) return forbidden();
      if (hasValidAdminSession) return NextResponse.redirect(new URL("/admin/dashboard", request.url));
      return NextResponse.next();
    }

    if (hasValidAdminSession) return NextResponse.next();
    if (hasSession || adminSession) return forbidden();
    return NextResponse.redirect(new URL("/admin/login", request.url));
  }

  if (pathname.startsWith("/dashboard") && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (isAuthRoute && hasSession && pathname === "/login") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/admin/:path*"],
};
