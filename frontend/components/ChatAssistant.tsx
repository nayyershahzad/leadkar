"use client";

import { useEffect, useRef, useState } from "react";

import { CustomOrderForm } from "@/components/CustomOrderForm";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { formatPKR } from "@/lib/utils";

interface Quote {
  quote_id: string;
  kind: "catalog" | "custom";
  title: string;
  price_pkr: number;
  guaranteed_min: number | null;
  likely_low: number | null;
  likely_high: number | null;
  preview_rows: Record<string, unknown>[];
}

interface Msg {
  role: "user" | "assistant";
  content: string;
}

const GREETING =
  "Hi! I'm here to put together a lead pack for you. Which city, what kind of " +
  "business, and roughly how many leads do you need?";

export function ChatAssistant() {
  // null = still checking; false = assistant off (show form); true = chat.
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [messages, setMessages] = useState<Msg[]>([{ role: "assistant", content: GREETING }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [customer, setCustomer] = useState({ email: "", name: "" });
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/assistant/status")
      .then((r) => (r.ok ? r.json() : { enabled: false }))
      .then((d) => setEnabled(Boolean(d.enabled)))
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, quote]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Only user/assistant turns are sent (the greeting is cosmetic, skip it).
        body: JSON.stringify({ messages: next.slice(1) }),
      });
      if (!res.ok) throw new Error(`Chat failed (${res.status})`);
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      if (data.quote) setQuote(data.quote as Quote);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function accept(e: React.FormEvent) {
    e.preventDefault();
    if (!quote || accepting) return;
    setAccepting(true);
    setError(null);
    try {
      const res = await fetch(`/api/assistant/quote/${quote.quote_id}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer }),
      });
      if (!res.ok) throw new Error(`Order failed (${res.status})`);
      const data = (await res.json()) as { payment_url: string };
      window.location.href = data.payment_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setAccepting(false);
    }
  }

  if (enabled === null) {
    return <div className="py-10 text-center text-sm text-slate-400">Loading…</div>;
  }
  if (enabled === false) {
    // Assistant unavailable → graceful fallback to the plain form (§15.2).
    return <CustomOrderForm />;
  }

  return (
    <div className="space-y-4">
      <div
        ref={scrollRef}
        className="max-h-80 space-y-3 overflow-y-auto rounded-xl bg-slate-50 p-4"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
          >
            <span
              className={
                "max-w-[85%] rounded-2xl px-4 py-2 text-sm " +
                (m.role === "user"
                  ? "bg-brand text-white"
                  : "bg-white text-slate-700 shadow-sm")
              }
            >
              {m.content}
            </span>
          </div>
        ))}
        {loading ? (
          <div className="flex justify-start">
            <span className="rounded-2xl bg-white px-4 py-2 text-sm text-slate-400 shadow-sm">
              typing…
            </span>
          </div>
        ) : null}
      </div>

      {quote ? (
        <div className="rounded-2xl border border-accent/30 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-bold text-slate-900">{quote.title}</p>
              {quote.kind === "custom" ? (
                <p className="mt-1 text-sm text-slate-600">
                  Guaranteed at least <strong>{quote.guaranteed_min}</strong> leads
                  {quote.likely_high ? (
                    <> (likely {quote.likely_low}–{quote.likely_high})</>
                  ) : null}
                  . Extras are free.
                </p>
              ) : (
                <p className="mt-1 text-sm text-emerald-600">Ready now — instant delivery.</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-2xl font-black text-slate-900">{formatPKR(quote.price_pkr)}</p>
            </div>
          </div>

          {quote.preview_rows.length > 0 ? (
            <div className="mt-4 overflow-x-auto rounded-lg border border-slate-100">
              <table className="w-full text-left text-xs">
                <tbody>
                  {quote.preview_rows.map((row, i) => (
                    <tr key={i} className="border-b border-slate-100 last:border-0">
                      <td className="px-3 py-1.5 font-medium text-slate-700">
                        {String((row as Record<string, unknown>).name ?? "—")}
                      </td>
                      <td className="px-3 py-1.5 text-slate-500">
                        {String((row as Record<string, unknown>).phone ?? "")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="px-3 py-1.5 text-[11px] text-slate-400">Sample preview</p>
            </div>
          ) : null}

          <form onSubmit={accept} className="mt-4 grid gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="qemail">Email *</Label>
              <Input
                id="qemail"
                type="email"
                required
                value={customer.email}
                onChange={(e) => setCustomer({ ...customer, email: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="qname">Name *</Label>
              <Input
                id="qname"
                required
                value={customer.name}
                onChange={(e) => setCustomer({ ...customer, name: e.target.value })}
              />
            </div>
            <Button
              type="submit"
              variant="gradient"
              size="lg"
              disabled={accepting}
              className="sm:col-span-2"
            >
              {accepting ? "Redirecting to payment…" : `Buy for ${formatPKR(quote.price_pkr)}`}
            </Button>
          </form>
        </div>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <form onSubmit={send} className="flex gap-2">
        <Input
          placeholder="e.g. 200 gyms in Multan"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          Send
        </Button>
      </form>
    </div>
  );
}
