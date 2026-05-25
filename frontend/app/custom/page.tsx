import { CustomOrderForm } from "@/components/CustomOrderForm";

export const metadata = { title: "Custom lead order — LeadKar" };

export default function CustomPage() {
  return (
    <>
      <section className="relative">
        <div className="blob left-1/3 -top-12 h-60 w-60 animate-blob bg-accent/40" />
        <div className="blob right-1/3 -top-8 h-60 w-60 animate-blob bg-brand/40 [animation-delay:4s]" />
        <div className="container relative max-w-2xl py-16 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-white/70 px-4 py-1.5 text-sm font-semibold text-accent backdrop-blur">
            ⚡ Built to order
          </span>
          <h1 className="mt-5 text-4xl font-black tracking-tight text-slate-900 sm:text-5xl">
            Your niche, <span className="text-gradient">scraped on demand</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-slate-600">
            Pick a city, business type, and how many leads you need. We scrape and verify them,
            then email your CSV + XLSX — usually within 24 hours.
          </p>
        </div>
      </section>

      <section className="container max-w-2xl pb-20">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <CustomOrderForm />
        </div>
      </section>
    </>
  );
}
