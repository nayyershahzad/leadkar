import Link from "next/link";
import {
  ArrowRight,
  Clock,
  CreditCard,
  Mail,
  MapPin,
  Phone,
  Sparkles,
  Wallet,
  Zap,
} from "lucide-react";

import { PackCard } from "@/components/PackCard";
import { Button } from "@/components/ui/button";
import { listPacks } from "@/lib/api";

const STEPS = [
  { icon: MapPin, title: "Pick your pack", body: "Choose a city + niche, or request a custom list. Hundreds of vetted leads, ready to go." },
  { icon: CreditCard, title: "Pay in PKR", body: "Secure checkout via PayPro — cards or bank transfer. No subscription, no lock-in." },
  { icon: Mail, title: "Check your inbox", body: "CSV + XLSX download links land in minutes. Import to your CRM and start dialing." },
];

const VALUES = [
  { icon: MapPin, title: "Pakistan-first data", body: "Real coverage of Karachi, Lahore, Islamabad & more — where Apollo and ZoomInfo fall flat." },
  { icon: Phone, title: "Phone-verified", body: "Numbers normalized to +92 and carrier-tagged, so you reach humans, not dead lines." },
  { icon: Wallet, title: "No subscription tax", body: "Pay once per pack. Keep the data. Built for bootstrappers, not enterprise budgets." },
  { icon: Zap, title: "Custom on demand", body: "Need a niche we don't stock? Spin up a custom scrape and get it the same day." },
];

const FAQ = [
  { q: "Where does the data come from?", a: "Google Maps, sourced via Apify — then cleaned, phone-verified, and carrier-tagged for Pakistan." },
  { q: "How fast do I get it?", a: "Catalog packs hit your inbox within minutes of payment. Custom orders within 24 hours." },
  { q: "Can I request a custom city or niche?", a: "Yes — set the city, business type, and lead count on the custom page and we scrape it on demand." },
  { q: "How do I pay?", a: "In PKR via PayPro — cards and bank transfer. One-time per pack, no recurring fees." },
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
      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-grid">
        <div className="blob left-[-6rem] top-[-4rem] h-72 w-72 animate-blob bg-brand/40" />
        <div className="blob right-[-4rem] top-10 h-72 w-72 animate-blob bg-accent/40 [animation-delay:3s]" />
        <div className="blob bottom-[-6rem] left-1/3 h-72 w-72 animate-blob bg-accent-pink/30 [animation-delay:6s]" />

        <div className="container relative py-20 text-center sm:py-28">
          <span className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-white/70 px-4 py-1.5 text-sm font-semibold text-brand backdrop-blur">
            <Sparkles className="h-4 w-4" /> Built for Pakistani founders &amp; hustlers 🇵🇰
          </span>

          <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-black leading-[1.05] tracking-tight text-slate-900 sm:text-6xl">
            Your next <span className="text-gradient">1,000 customers</span>,
            <br className="hidden sm:block" /> ready to download.
          </h1>

          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600">
            Skip the cold DMs and guesswork. Get curated, phone-verified business leads for any
            Pakistani city or niche — PKR-priced, delivered as CSV + XLSX. Buy a pack, hit send.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/packs">
              <Button variant="gradient" size="lg" className="gap-2">
                Browse lead packs <ArrowRight className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/custom">
              <Button variant="outline" size="lg">
                Build a custom list
              </Button>
            </Link>
          </div>

          <div className="mx-auto mt-10 flex max-w-2xl flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm font-medium text-slate-600">
            <span className="inline-flex items-center gap-1.5"><Phone className="h-4 w-4 text-brand" /> Phone + carrier tagged</span>
            <span className="inline-flex items-center gap-1.5"><Clock className="h-4 w-4 text-brand" /> Delivered in minutes</span>
            <span className="inline-flex items-center gap-1.5"><Wallet className="h-4 w-4 text-brand" /> From Rs 3,999</span>
            <span className="inline-flex items-center gap-1.5"><Zap className="h-4 w-4 text-brand" /> Zero subscriptions</span>
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="container py-20">
        <h2 className="text-center text-3xl font-black text-slate-900">Leads in 3 steps</h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-slate-500">
          No demos, no sales calls. From browse to inbox in under five minutes.
        </p>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="relative rounded-2xl border border-slate-200 bg-white p-6">
              <span className="absolute right-5 top-5 text-5xl font-black text-slate-100">{i + 1}</span>
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-brand to-accent text-white">
                <s.icon className="h-6 w-6" />
              </div>
              <h3 className="mt-4 text-lg font-bold text-slate-900">{s.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Popular packs ─────────────────────────────────────── */}
      {packs.length > 0 ? (
        <section className="container pb-20">
          <div className="mb-8 flex items-end justify-between">
            <div>
              <h2 className="text-3xl font-black text-slate-900">🔥 Popular packs</h2>
              <p className="mt-1 text-slate-500">Grab-and-go lists founders are buying right now.</p>
            </div>
            <Link href="/packs" className="hidden text-sm font-semibold text-brand hover:text-brand-dark sm:inline-flex sm:items-center sm:gap-1">
              See all <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {packs.map((pack) => (
              <PackCard key={pack.id} pack={pack} />
            ))}
          </div>
        </section>
      ) : null}

      {/* ── Why LeadKar ───────────────────────────────────────── */}
      <section className="bg-slate-50">
        <div className="container py-20">
          <h2 className="text-center text-3xl font-black text-slate-900">Why hustlers pick LeadKar</h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {VALUES.map((v) => (
              <div key={v.title} className="rounded-2xl border border-slate-200 bg-white p-6 transition-shadow hover:shadow-md">
                <div className="grid h-11 w-11 place-items-center rounded-xl bg-brand/10 text-brand">
                  <v.icon className="h-5 w-5" />
                </div>
                <h3 className="mt-4 font-bold text-slate-900">{v.title}</h3>
                <p className="mt-1 text-sm text-slate-600">{v.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────── */}
      <section className="container py-20">
        <h2 className="text-3xl font-black text-slate-900">Questions, answered</h2>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {FAQ.map((item) => (
            <div key={item.q} className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="font-bold text-slate-900">{item.q}</h3>
              <p className="mt-1 text-sm text-slate-600">{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ─────────────────────────────────────────── */}
      <section className="container pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand via-accent to-accent-pink px-8 py-16 text-center text-white">
          <div className="blob right-10 top-0 h-40 w-40 bg-white/20" />
          <h2 className="relative mx-auto max-w-2xl text-3xl font-black sm:text-4xl">
            Stop chasing leads. Start closing them.
          </h2>
          <p className="relative mx-auto mt-3 max-w-xl text-white/90">
            Verified Pakistani business leads, priced in rupees, in your inbox today.
          </p>
          <div className="relative mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href="/packs">
              <Button size="lg" className="gap-2 bg-white text-brand hover:bg-white/90">
                Browse packs <ArrowRight className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/custom">
              <Button size="lg" variant="outline" className="border-white/60 bg-transparent text-white hover:bg-white/10">
                Custom order
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
