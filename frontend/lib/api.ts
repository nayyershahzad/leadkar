// Server-side API access to the FastAPI backend. Browser calls go through the
// /api rewrite in next.config.mjs; server components use the internal URL.

const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://backend:8000";

export interface Pack {
  id: string;
  slug: string;
  title: string;
  city: string;
  vertical: string;
  lead_count: number;
  price_pkr: number;
  description: string | null;
  sample_preview: { rows?: Record<string, unknown>[] } | Record<string, unknown>[] | null;
  last_refreshed_at: string | null;
}

export interface OrderCreateResponse {
  order_id: string;
  payment_url: string;
  status: string;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_INTERNAL_URL}/api${path}`, {
    // Catalog changes rarely; revalidate periodically.
    next: { revalidate: 60 },
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function listPacks(): Promise<Pack[]> {
  return getJSON<Pack[]>("/packs");
}

export async function getPack(slug: string): Promise<Pack | null> {
  const res = await fetch(`${API_INTERNAL_URL}/api/packs/${encodeURIComponent(slug)}`, {
    next: { revalidate: 60 },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API /packs/${slug} failed: ${res.status}`);
  return res.json() as Promise<Pack>;
}

/** Normalize sample_preview (dict {rows:[]} or list) into an array of rows. */
export function sampleRows(pack: Pack): Record<string, unknown>[] {
  const sp = pack.sample_preview;
  if (!sp) return [];
  if (Array.isArray(sp)) return sp.slice(0, 3);
  if (Array.isArray(sp.rows)) return sp.rows.slice(0, 3);
  return [];
}
