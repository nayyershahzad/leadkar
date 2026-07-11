import { sampleRows, type Pack } from "@/lib/api";

export function PricingTable({ pack }: { pack: Pack }) {
  const rows = sampleRows(pack);
  if (rows.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        Sample preview available after purchase.
      </p>
    );
  }
  const scored = rows.some((r) => r.signal_tags != null || r.whatsapp != null);
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Name</th>
            <th className="px-3 py-2 font-medium">Category</th>
            <th className="px-3 py-2 font-medium">Phone</th>
            {scored ? <th className="px-3 py-2 font-medium">Signals</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-slate-100 align-top">
              <td className="px-3 py-2 font-medium text-slate-800">
                {String(row.name ?? "—")}
              </td>
              <td className="px-3 py-2 text-slate-600">{String(row.category ?? "—")}</td>
              <td className="px-3 py-2 text-slate-600">{String(row.phone ?? "—")}</td>
              {scored ? (
                <td className="px-3 py-2">
                  <TagList tags={row.signal_tags} whatsapp={Boolean(row.whatsapp)} />
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TagList({ tags, whatsapp }: { tags: unknown; whatsapp: boolean }) {
  const list =
    typeof tags === "string"
      ? tags.split("|").filter(Boolean)
      : Array.isArray(tags)
        ? tags.map(String)
        : [];
  if (list.length === 0 && !whatsapp) return <span className="text-slate-400">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {list.map((t) => (
        <span
          key={t}
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${tagTone(t)}`}
        >
          {t.replace(/_/g, " ")}
        </span>
      ))}
    </div>
  );
}

function tagTone(tag: string): string {
  if (tag === "whatsapp_reachable") return "bg-green-100 text-green-700";
  if (tag === "hidden_gem") return "bg-brand/10 text-brand";
  if (tag === "unclaimed" || tag === "no_website") return "bg-amber-100 text-amber-700";
  if (tag === "reputation_risk" || tag === "closed") return "bg-red-100 text-red-700";
  return "bg-slate-100 text-slate-600";
}
