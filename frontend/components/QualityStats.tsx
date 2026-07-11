import { MessageCircle, Sparkles, Star, Globe, Phone, Mail } from "lucide-react";

import { type PackStats } from "@/lib/api";

/** Turn a percentage + pack size into a concrete "121 of 136" style count. */
function countOf(pct: number, total: number): number {
  return Math.round((pct / 100) * total);
}

/** Compact quality chips for the pack card (Wave 1 wow).
 *  Positive counts only — never a raw average "grade", which reads as a fail
 *  and scares buyers off a list that's already an order-of-magnitude cheap. */
export function QualityChips({ stats }: { stats: PackStats }) {
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {stats.pct_whatsapp > 0 ? (
        <Chip>
          <MessageCircle className="h-3 w-3" /> {stats.pct_whatsapp}% WhatsApp
        </Chip>
      ) : null}
      {stats.hidden_gems > 0 ? (
        <Chip>
          <Sparkles className="h-3 w-3" /> {stats.hidden_gems} hidden gems
        </Chip>
      ) : null}
      {stats.pct_phone > 0 ? (
        <Chip>
          <Phone className="h-3 w-3" /> {stats.pct_phone}% direct phone
        </Chip>
      ) : null}
    </div>
  );
}

/** Full quality grid for the pack detail page. Concrete "N of total" counts,
 *  best-first framing — no visible 0–100 score. */
export function QualitySummary({ stats }: { stats: PackStats }) {
  const total = stats.lead_count;
  const cells = [
    {
      label: "Direct phone",
      value: `${countOf(stats.pct_phone, total).toLocaleString()} of ${total.toLocaleString()}`,
      icon: Phone,
    },
    {
      label: "WhatsApp-reachable",
      value: `${stats.pct_whatsapp}%`,
      icon: MessageCircle,
    },
    { label: "Has email", value: `${stats.pct_email}%`, icon: Mail },
    { label: "Has website", value: `${stats.pct_website}%`, icon: Globe },
  ];
  return (
    <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-brand/5 to-accent/5 p-5">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <Sparkles className="h-4 w-4 text-brand" /> What&apos;s inside
        {stats.hidden_gems > 0 ? (
          <span className="ml-auto rounded-full bg-brand/10 px-2.5 py-0.5 text-xs font-semibold text-brand">
            {stats.hidden_gems} hidden gems
          </span>
        ) : null}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {cells.map((c) => (
          <div key={c.label} className="flex flex-col">
            <dt className="flex items-center gap-1 text-xs font-medium text-slate-500">
              <c.icon className="h-3.5 w-3.5" /> {c.label}
            </dt>
            <dd className="mt-1 text-2xl font-extrabold text-slate-900">{c.value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 flex items-start gap-1.5 text-xs text-slate-500">
        <Star className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
        <span>
          Every lead is ranked on contactability, business quality &amp; digital maturity,
          then delivered <strong>best-first</strong> — your strongest prospects sit at the
          top of the file. WhatsApp is a likelihood flag on Pakistani mobile numbers, not a
          verified opt-in.
        </span>
      </p>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
      {children}
    </span>
  );
}
