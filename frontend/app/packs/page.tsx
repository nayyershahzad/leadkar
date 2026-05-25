import { PackCard } from "@/components/PackCard";
import { listPacks } from "@/lib/api";

export const metadata = { title: "Lead packs — LeadKar" };

export default async function PacksPage() {
  let packs = [] as Awaited<ReturnType<typeof listPacks>>;
  let failed = false;
  try {
    packs = await listPacks();
  } catch {
    failed = true;
  }

  return (
    <div className="container py-12">
      <h1 className="text-3xl font-bold text-slate-900">Lead packs</h1>
      <p className="mt-2 text-slate-600">
        Off-the-shelf, pre-verified lead lists. Buy, pay in PKR, download instantly.
      </p>

      {failed ? (
        <p className="mt-10 text-slate-500">Packs are temporarily unavailable. Please try again.</p>
      ) : packs.length === 0 ? (
        <p className="mt-10 text-slate-500">No packs available yet — check back soon.</p>
      ) : (
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {packs.map((pack) => (
            <PackCard key={pack.id} pack={pack} />
          ))}
        </div>
      )}
    </div>
  );
}
