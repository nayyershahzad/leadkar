import { notFound } from "next/navigation";

import { BuyButton } from "@/components/BuyButton";
import { PricingTable } from "@/components/PricingTable";
import { Card, CardContent } from "@/components/ui/card";
import { getPack } from "@/lib/api";
import { formatPKR, prettify } from "@/lib/utils";

export default async function PackDetailPage({ params }: { params: { slug: string } }) {
  const pack = await getPack(params.slug);
  if (!pack) notFound();

  return (
    <div className="container py-12">
      <div className="grid gap-10 lg:grid-cols-[1fr_360px]">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-brand">
            {pack.city} · {prettify(pack.vertical)}
          </p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">{pack.title}</h1>
          <p className="mt-2 text-slate-600">
            {pack.lead_count.toLocaleString()} verified leads
          </p>
          {pack.description ? (
            <p className="mt-4 text-slate-700">{pack.description}</p>
          ) : null}

          <h2 className="mt-10 text-lg font-semibold text-slate-900">Sample preview</h2>
          <div className="mt-3">
            <PricingTable pack={pack} />
          </div>
        </div>

        <aside>
          <Card className="sticky top-6">
            <CardContent className="pt-5">
              <p className="text-3xl font-extrabold text-slate-900">{formatPKR(pack.price_pkr)}</p>
              <p className="mt-1 text-sm text-slate-500">One-time · CSV + XLSX</p>
              <div className="mt-5">
                <BuyButton packSlug={pack.slug} />
              </div>
              <ul className="mt-5 space-y-1 text-sm text-slate-600">
                <li>✓ {pack.lead_count.toLocaleString()} verified leads</li>
                <li>✓ Phone + carrier tagged</li>
                <li>✓ Instant email delivery</li>
              </ul>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
