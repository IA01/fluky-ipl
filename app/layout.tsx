import type { Metadata } from "next";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://fluky-ipl.vercel.app"),
  title: { default: "How Fluky Was the IPL?", template: "%s · How Fluky?" },
  description: "Every IPL season, replayed. Skill gets a rating. Luck gets a number.",
  openGraph: {
    title: "How Fluky Was the IPL?",
    description: "19 seasons. 190,000 alternate histories. One question: did the best team win?",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">Skip to content</a>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
