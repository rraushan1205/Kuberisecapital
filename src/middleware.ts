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

async function verifyJwtToken(token: string | undefined) {
  const secret = process.env.JWT_SECRET_KEY;
  if (!token || !secret) return null;
  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(secret), { algorithms: ["HS256"] });
    return payload;
  } catch {
    return null;
  }
}

async function hasValidSuperAdminSession(token: string | undefined) {
  const payload = await verifyJwtToken(token);
  return payload?.role === "SUPER_ADMIN";
}

async function hasValidUserSession(token: string | undefined) {
  const payload = await verifyJwtToken(token);
  return payload !== null;
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Get tokens from cookies
  const userToken = request.cookies.get("stratum_token")?.value;
  const adminToken = request.cookies.get("stratum_admin_session")?.value;
  
  // Validate tokens
  const hasValidUserToken = await hasValidUserSession(userToken);
  const hasValidAdminToken = await hasValidSuperAdminSession(adminToken);
  
  const isAuthRoute = authRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );

  // Admin routes protection
  if (pathname.startsWith("/admin")) {
    if (pathname === "/admin/login") {
      // If user has valid user token but not admin, forbid access
      if (hasValidUserToken && !hasValidAdminToken) return forbidden();
      // If already logged in as admin, redirect to dashboard
      if (hasValidAdminToken) return NextResponse.redirect(new URL("/admin/dashboard", request.url));
      return NextResponse.next();
    }

    // All other admin routes require valid admin token
    if (hasValidAdminToken) return NextResponse.next();
    // If has user token or invalid admin token, forbid
    if (hasValidUserToken || adminToken) return forbidden();
    // Otherwise redirect to admin login
    return NextResponse.redirect(new URL("/admin/login", request.url));
  }

  // User dashboard routes protection - require valid JWT token
  if (pathname.startsWith("/dashboard")) {
    if (!hasValidUserToken) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next();
  }

  // Redirect logged-in users away from login page
  if (isAuthRoute && hasValidUserToken && pathname === "/login") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/admin/:path*"],
};
