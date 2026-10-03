import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProjectPulse — Project workspace",
  description: "Project intelligence and decision reconciliation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
