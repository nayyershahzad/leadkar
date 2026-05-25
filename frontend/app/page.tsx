import Link from "next/link";

import { PackCard } from "@/components/PackCard";
import { Button } from "@/components/ui/button";
import { listPacks } from "@/lib/api";

const FAQ = [
  {
    q: "Where does the data come from?",
    a: "We source from Google Maps via Apify, then normalize and verify phone numbers and emails for the Pakistani market.",
  },
  {
    q: "How is it delivered?",
    a: "As CSV + XLSX files via secure, time-limited download links emailed to you after payment.",
  },
  {
    q: "Can I request a custom city or vertical?",
    a: "Yes — use a custom order. Tell us the city, business type, and how many leads you need.",
  },
  {
    q: "How do I pay?",
    a: "Securely in PKR via PayPro (cards and bank transfer).",
  },
];

export default async function HomePage() {
  let packs = [] as Awaited<ReturnType<typeof listPacks>>;
  try {
    packs = (await listPacks()).slice(0, 3);
  } catch {
    packs = [];
  }

  return (
    <>
      <section className="bg-gradient-to-b from-slate-50 to-white">
        <div className="container py-20 text-center">
          <h1 className="mx-auto max-w-3xl text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            Verified Pakistani business leads, priced in rupees.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600">
            Apollo and ZoomInfo have weak Pakistan data at Western prices. LeadKar gives you
            curated Google Maps leads for Pakistani cities and verticals — as ready-made packs or
            custom orders.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link href="/packs">
              <Button size="lg">Browse packs</Button>
            </Link>
            <Link href="/custom">
              <Button size="lg" variant="outline">
                Custom order
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {packs.length > 0 ? (
        <section className="container py-16">
          <div className="mb-8 flex items-end justify-between">
            <h2 className="text-2xl font-bold text-slate-900">Popular packs</h2>
            <Link href="/packs" className="text-sm font-medium text-brand hover:text-brand-dark">
              See all →
            </Link>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {packs.map((pack) => (
              <PackCard key={pack.id} pack={pack} />
            ))}
          </div>
        </section>
      ) : null}

      <section className="bg-slate-50">
        <div className="container py-16">
          <h2 className="mb-8 text-2xl font-bold text-slate-900">Frequently asked questions</h2>
          <div className="grid gap-6 md:grid-cols-2">
            {FAQ.map((item) => (
              <div key={item.q}>
                <h3 className="font-semibold text-slate-900">{item.q}</h3>
                <p className="mt-1 text-sm text-slate-600">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
