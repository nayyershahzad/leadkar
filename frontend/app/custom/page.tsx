import { CustomOrderForm } from "@/components/CustomOrderForm";

export const metadata = { title: "Custom lead order — LeadKar" };

export default function CustomPage() {
  return (
    <div className="container max-w-2xl py-12">
      <h1 className="text-3xl font-bold text-slate-900">Custom lead order</h1>
      <p className="mt-2 text-slate-600">
        Tell us the city, business type, and how many leads you need. We scrape and verify them
        on demand, then email your CSV + XLSX.
      </p>
      <div className="mt-8">
        <CustomOrderForm />
      </div>
    </div>
  );
}
