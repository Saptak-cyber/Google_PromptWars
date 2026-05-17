import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "LexGuard — AI Contract Intelligence",
  description: "Analyze contracts, offer letters, and legal policies for exploitative clauses, hidden liabilities, and real-world risks before you sign.",
  keywords: ["contract analysis", "AI legal", "risk detection", "contract intelligence"],
  openGraph: {
    title: "LexGuard — AI Contract Intelligence",
    description: "Know what you're signing. AI-powered adversarial contract analysis.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-gray-950 text-gray-100 antialiased">{children}</body>
    </html>
  );
}
