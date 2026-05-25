import Link from "next/link";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";

export const metadata = { title: "Order received — LeadKar" };

export default function OrderSuccessPage({
  searchParams,
}: {
  searchParams: { order_id?: string };
}) {
  return (
    <div className="container max-w-xl py-24 text-center">
      <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-brand to-accent text-white shadow-lg shadow-accent/30">
        <Check className="h-8 w-8" />
      </div>
      <h1 className="mt-6 text-3xl font-black text-slate-900">You&apos;re all set! 🎉</h1>
      <p className="mt-3 text-slate-600">
        Payment received — we&apos;re preparing your leads. Secure download links are on their way
        to your inbox: catalog packs in minutes, custom orders within 24 hours.
      </p>
      {searchParams.order_id ? (
        <p className="mt-4 text-sm text-slate-400">Order reference: {searchParams.order_id}</p>
      ) : null}
      <div className="mt-8">
        <Link href="/packs">
          <Button variant="gradient" size="lg">
            Browse more packs
          </Button>
        </Link>
      </div>
    </div>
  );
}
