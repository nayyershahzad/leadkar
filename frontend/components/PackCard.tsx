import Link from "next/link";

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { type Pack } from "@/lib/api";
import { formatPKR, prettify } from "@/lib/utils";

export function PackCard({ pack }: { pack: Pack }) {
  return (
    <Card className="flex flex-col transition-shadow hover:shadow-md">
      <CardHeader>
        <p className="text-xs font-medium uppercase tracking-wide text-brand">
          {pack.city} · {prettify(pack.vertical)}
        </p>
        <CardTitle className="mt-1">{pack.title}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        <p className="text-sm text-slate-600">
          {pack.lead_count.toLocaleString()} verified leads
        </p>
        {pack.description ? (
          <p className="mt-2 line-clamp-2 text-sm text-slate-500">{pack.description}</p>
        ) : null}
      </CardContent>
      <CardFooter className="flex items-center justify-between">
        <span className="text-xl font-bold text-slate-900">{formatPKR(pack.price_pkr)}</span>
        <Link
          href={`/packs/${pack.slug}`}
          className="text-sm font-medium text-brand hover:text-brand-dark"
        >
          View details →
        </Link>
      </CardFooter>
    </Card>
  );
}
