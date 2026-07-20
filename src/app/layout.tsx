import type { Metadata } from "next";
import "./globals.css";
import { AppProviders } from "@/providers/app-providers";

export const metadata: Metadata = {
  title: {
    default: "Stratum | Secure access",
    template: "%s | Stratum",
  },
  description: "Secure access to the Stratum trading platform.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body><AppProviders>{children}</AppProviders></body>
    </html>
  );
}
