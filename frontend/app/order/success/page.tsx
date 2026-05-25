import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata = { title: "Order received — LeadKar" };

export default function OrderSuccessPage({
  searchParams,
}: {
  searchParams: { order_id?: string };
}) {
  return (
    <div className="container max-w-xl py-20 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-100 text-2xl">
        ✓
      </div>
      <h1 className="mt-6 text-3xl font-bold text-slate-900">Payment received</h1>
      <p className="mt-3 text-slate-600">
        We&apos;re preparing your leads. You&apos;ll get an email with secure download links —
        catalog packs arrive within minutes, custom orders within 24 hours.
      </p>
      {searchParams.order_id ? (
        <p className="mt-4 text-sm text-slate-400">Order reference: {searchParams.order_id}</p>
      ) : null}
      <div className="mt-8">
        <Link href="/packs">
          <Button variant="outline">Browse more packs</Button>
        </Link>
      </div>
    </div>
  );
}
