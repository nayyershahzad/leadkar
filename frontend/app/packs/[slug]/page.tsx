import Link from "next/link";
import { notFound } from "next/navigation";
import { Check, Mail, Phone } from "lucide-react";

import { BuyButton } from "@/components/BuyButton";
import { PricingTable } from "@/components/PricingTable";
import { QualitySummary } from "@/components/QualityStats";
import { getPack, packStats } from "@/lib/api";
import { formatPKR, prettify } from "@/lib/utils";

export default async function PackDetailPage({ params }: { params: { slug: string } }) {
  const pack = await getPack(params.slug);
  if (!pack) notFound();
  const stats = packStats(pack);

  return (
    <div className="container py-10">
      <nav className="text-sm text-slate-500">
        <Link href="/packs" className="hover:text-brand">
          Packs
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700">{pack.title}</span>
      </nav>

      <div className="mt-6 grid gap-10 lg:grid-cols-[1fr_380px]">
        <div>
          <span className="w-fit rounded-full bg-brand/10 px-3 py-1 text-xs font-semibold text-brand">
            {pack.city} · {prettify(pack.vertical)}
          </span>
          <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-900">{pack.title}</h1>
          <p className="mt-2 font-medium text-slate-500">
            {pack.lead_count.toLocaleString()} verified leads
          </p>
          {pack.description ? <p className="mt-4 text-slate-700">{pack.description}</p> : null}

          {stats ? (
            <div className="mt-8">
              <QualitySummary stats={stats} />
            </div>
          ) : null}

          <h2 className="mt-10 text-lg font-bold text-slate-900">Sample preview</h2>
          <div className="mt-3">
            <PricingTable pack={pack} />
          </div>
        </div>

        <aside>
          <div className="sticky top-24 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="bg-gradient-to-r from-brand to-accent bg-clip-text text-4xl font-extrabold text-transparent">
              {formatPKR(pack.price_pkr)}
            </p>
            <p className="mt-1 text-sm text-slate-500">One-time · CSV + XLSX · instant delivery</p>
            <div className="mt-5">
              <BuyButton packSlug={pack.slug} />
            </div>
            <ul className="mt-6 space-y-2 text-sm text-slate-600">
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-brand" /> {pack.lead_count.toLocaleString()} verified leads
              </li>
              <li className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-brand" /> Phone + carrier tagged
              </li>
              <li className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-brand" /> Emailed download links
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
