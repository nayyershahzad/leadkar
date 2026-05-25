import { sampleRows, type Pack } from "@/lib/api";

const PREVIEW_COLUMNS = ["name", "category", "phone", "website"] as const;

export function PricingTable({ pack }: { pack: Pack }) {
  const rows = sampleRows(pack);
  if (rows.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        Sample preview available after purchase.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            {PREVIEW_COLUMNS.map((col) => (
              <th key={col} className="px-3 py-2 font-medium capitalize">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-slate-100">
              {PREVIEW_COLUMNS.map((col) => (
                <td key={col} className="px-3 py-2 text-slate-700">
                  {String(row[col] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
