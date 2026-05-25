import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { type Pack } from "@/lib/api";
import { formatPKR, prettify } from "@/lib/utils";

export function PackCard({ pack }: { pack: Pack }) {
  return (
    <Link
      href={`/packs/${pack.slug}`}
      className="group relative flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-brand/40 hover:shadow-xl"
    >
      {/* hover glow */}
      <div className="absolute inset-x-0 -top-px h-1 scale-x-0 bg-gradient-to-r from-brand to-accent transition-transform duration-300 group-hover:scale-x-100" />

      <span className="w-fit rounded-full bg-brand/10 px-3 py-1 text-xs font-semibold text-brand">
        {pack.city} · {prettify(pack.vertical)}
      </span>

      <h3 className="mt-3 text-lg font-bold text-slate-900">{pack.title}</h3>
      <p className="mt-1 text-sm font-medium text-slate-500">
        {pack.lead_count.toLocaleString()} verified leads
      </p>
      {pack.description ? (
        <p className="mt-2 line-clamp-2 flex-1 text-sm text-slate-500">{pack.description}</p>
      ) : (
        <div className="flex-1" />
      )}

      <div className="mt-5 flex items-center justify-between">
        <span className="bg-gradient-to-r from-brand to-accent bg-clip-text text-2xl font-extrabold text-transparent">
          {formatPKR(pack.price_pkr)}
        </span>
        <span className="inline-flex items-center gap-1 text-sm font-semibold text-brand transition-transform group-hover:translate-x-0.5">
          View <ArrowRight className="h-4 w-4" />
        </span>
      </div>
    </Link>
  );
}
