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
    <>
      <section className="relative overflow-hidden bg-grid">
        <div className="blob left-[-4rem] top-[-3rem] h-60 w-60 animate-blob bg-brand/40" />
        <div className="blob right-[-3rem] top-6 h-60 w-60 animate-blob bg-accent/40 [animation-delay:4s]" />
        <div className="container relative py-16 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-white/70 px-4 py-1.5 text-sm font-semibold text-brand backdrop-blur">
            🔥 Grab-and-go lead lists
          </span>
          <h1 className="mx-auto mt-5 max-w-2xl text-4xl font-black tracking-tight text-slate-900 sm:text-5xl">
            Lead packs, ready to <span className="text-gradient">download</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-slate-600">
            Pre-verified lists by city and niche. Buy, pay in PKR, and import to your CRM in minutes.
          </p>
        </div>
      </section>

      <section className="container pb-20 pt-4">
        {failed ? (
          <p className="mt-6 text-center text-slate-500">
            Packs are temporarily unavailable. Please try again.
          </p>
        ) : packs.length === 0 ? (
          <p className="mt-6 text-center text-slate-500">No packs available yet — check back soon.</p>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {packs.map((pack) => (
              <PackCard key={pack.id} pack={pack} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
