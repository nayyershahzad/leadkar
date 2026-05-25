import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://leadkar.engstech.com"),
  title: "LeadKar — Verified Pakistani business leads, on demand",
  description:
    "Skip the cold DMs. Curated, phone-verified Google Maps leads for every Pakistani city and niche — PKR-priced, delivered as CSV + XLSX. No subscriptions.",
  openGraph: {
    title: "LeadKar — Verified Pakistani business leads",
    description:
      "Curated, phone-verified Google Maps leads for any Pakistani city or niche. PKR-priced, delivered as CSV + XLSX.",
    url: "https://leadkar.engstech.com",
    siteName: "LeadKar",
    images: ["/logo.png"],
    type: "website",
  },
  twitter: { card: "summary_large_image", title: "LeadKar", images: ["/logo.png"] },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-white">
        <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/80 backdrop-blur-md">
          <div className="container flex h-16 items-center justify-between">
            <Link href="/" className="flex items-center" aria-label="LeadKar home">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/logo-banner.png"
                alt="LeadKar"
                className="h-9 w-auto rounded-md sm:h-10"
              />
            </Link>
            <nav className="flex items-center gap-2 sm:gap-5 text-sm font-semibold text-slate-700">
              <Link href="/packs" className="hidden px-2 hover:text-brand sm:block">
                Packs
              </Link>
              <Link href="/custom" className="hidden px-2 hover:text-brand sm:block">
                Custom
              </Link>
              <Link href="/packs">
                <Button variant="gradient" size="sm">
                  Browse packs
                </Button>
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="mt-10 bg-ink text-slate-300">
          <div className="container flex flex-col items-center justify-between gap-3 py-10 sm:flex-row">
            <div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-banner.png" alt="LeadKar" className="h-9 w-auto rounded-md" />
              <p className="mt-2 text-sm text-slate-400">Digitizing Pakistani sales. 🇵🇰</p>
            </div>
            <div className="flex gap-6 text-sm">
              <Link href="/packs" className="hover:text-white">
                Packs
              </Link>
              <Link href="/custom" className="hover:text-white">
                Custom order
              </Link>
            </div>
          </div>
          <div className="border-t border-white/10 py-4 text-center text-xs text-slate-500">
            © {new Date().getFullYear()} LeadKar · PKR pricing · CSV + XLSX delivery
          </div>
        </footer>
      </body>
    </html>
  );
}
