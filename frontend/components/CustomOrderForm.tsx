"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { formatPKR } from "@/lib/utils";

// Estimate only — the authoritative price is computed by the backend at order
// creation. Keep in sync with CUSTOM_ORDER_BASE_PKR / PER_LEAD_PKR.
const BASE_PKR = Number(process.env.NEXT_PUBLIC_CUSTOM_BASE_PKR ?? 4999);
const PER_LEAD_PKR = Number(process.env.NEXT_PUBLIC_CUSTOM_PER_LEAD_PKR ?? 3);
const MAX_LEADS = Number(process.env.NEXT_PUBLIC_MAX_LEADS ?? 2500);

export function CustomOrderForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [spec, setSpec] = useState({ city: "", vertical: "", target_count: 300, notes: "" });
  const [customer, setCustomer] = useState({ email: "", name: "", phone: "", company: "" });

  const count = Math.min(Math.max(spec.target_count || 0, 0), MAX_LEADS);
  const estimate = BASE_PKR + PER_LEAD_PKR * count;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/orders/custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer, custom_spec: { ...spec, target_count: count } }),
      });
      if (!res.ok) throw new Error(`Order failed (${res.status})`);
      const data = (await res.json()) as { payment_url: string };
      window.location.href = data.payment_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="city">City *</Label>
          <Input
            id="city"
            required
            placeholder="Karachi"
            value={spec.city}
            onChange={(e) => setSpec({ ...spec, city: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="vertical">Business type *</Label>
          <Input
            id="vertical"
            required
            placeholder="restaurants"
            value={spec.vertical}
            onChange={(e) => setSpec({ ...spec, vertical: e.target.value })}
          />
        </div>
      </div>

      <div>
        <Label htmlFor="count">Number of leads * (max {MAX_LEADS.toLocaleString()})</Label>
        <Input
          id="count"
          type="number"
          min={1}
          max={MAX_LEADS}
          required
          value={spec.target_count}
          onChange={(e) => setSpec({ ...spec, target_count: Number(e.target.value) })}
        />
      </div>

      <div>
        <Label htmlFor="notes">Notes (optional)</Label>
        <Textarea
          id="notes"
          value={spec.notes}
          onChange={(e) => setSpec({ ...spec, notes: e.target.value })}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="cemail">Email *</Label>
          <Input
            id="cemail"
            type="email"
            required
            value={customer.email}
            onChange={(e) => setCustomer({ ...customer, email: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="cname">Name *</Label>
          <Input
            id="cname"
            required
            value={customer.name}
            onChange={(e) => setCustomer({ ...customer, name: e.target.value })}
          />
        </div>
      </div>

      <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
        <span className="text-sm text-slate-600">Estimated price</span>
        <span className="text-lg font-bold text-slate-900">{formatPKR(estimate)}</span>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Button type="submit" size="lg" disabled={loading} className="w-full">
        {loading ? "Redirecting to payment…" : "Continue to payment"}
      </Button>
    </form>
  );
}
