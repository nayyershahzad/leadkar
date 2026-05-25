import Link from "next/link";
import { AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

export const metadata = { title: "Payment incomplete — LeadKar" };

export default function OrderPendingPage() {
  return (
    <div className="container max-w-xl py-24 text-center">
      <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-amber-100 text-amber-600">
        <AlertCircle className="h-8 w-8" />
      </div>
      <h1 className="mt-6 text-3xl font-black text-slate-900">Payment not completed</h1>
      <p className="mt-3 text-slate-600">
        No charge was made. Your order is still waiting — give it another go whenever you&apos;re ready.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/packs">
          <Button variant="gradient" size="lg">
            Try again
          </Button>
        </Link>
        <Link href="/">
          <Button variant="ghost" size="lg">
            Back home
          </Button>
        </Link>
      </div>
    </div>
  );
}
