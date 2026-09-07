import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "How Fluky Was the IPL?",
  description: "Every IPL season, replayed. Skill gets a rating. Luck gets a number.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

