import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata = { title: "Payment incomplete — LeadKar" };

export default function OrderPendingPage() {
  return (
    <div className="container max-w-xl py-20 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-2xl">
        !
      </div>
      <h1 className="mt-6 text-3xl font-bold text-slate-900">Payment not completed</h1>
      <p className="mt-3 text-slate-600">
        Your payment wasn&apos;t completed, so no charge was made. You can try again — your order
        is waiting.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/packs">
          <Button>Try again</Button>
        </Link>
        <Link href="/">
          <Button variant="ghost">Back home</Button>
        </Link>
      </div>
    </div>
  );
}
