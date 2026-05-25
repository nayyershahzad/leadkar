import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "LeadKar — Verified Pakistani business leads",
  description:
    "Curated, verified Google Maps business leads for Pakistan. Off-the-shelf packs or custom orders, PKR-priced, delivered as CSV + XLSX.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col">
        <header className="border-b border-slate-200">
          <div className="container flex h-16 items-center justify-between">
            <Link href="/" className="text-xl font-extrabold text-brand">
              LeadKar
            </Link>
            <nav className="flex items-center gap-6 text-sm font-medium text-slate-700">
              <Link href="/packs" className="hover:text-brand">
                Packs
              </Link>
              <Link href="/custom" className="hover:text-brand">
                Custom order
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-slate-200 py-8">
          <div className="container flex flex-col items-center justify-between gap-2 text-sm text-slate-500 sm:flex-row">
            <p>© {new Date().getFullYear()} LeadKar — Digitizing Pakistani sales.</p>
            <p>PKR pricing · CSV + XLSX delivery</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
