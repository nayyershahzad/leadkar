# LeadKar

LeadKar is a Pakistan-focused B2B lead-generation product: Pakistani agencies, SMBs,
and marketers buy curated, verified Google Maps business listings as off-the-shelf
PKR-priced packs (catalog) or custom on-demand orders, delivered as CSV + XLSX via
emailed download links, paid through PayPro. The stack is FastAPI + SQLAlchemy 2.x +
Celery + Redis + Postgres on the backend, Next.js + Tailwind/shadcn on the frontend,
with Apify (`compass/crawler-google-places`) for scraping and Hetzner Object Storage
for deliverables — all running under Docker Compose behind Nginx on a Hetzner VPS.

**The full build specification is [`CLAUDE.md`](./CLAUDE.md) — read it end-to-end
before writing any code.** It is the source of truth for architecture, schema,
integrations, the phased build plan, and the non-negotiable rules.

## Deployment note (this host)

This instance is a **shared** Hetzner box (also running nexus, forestwatch,
invoicegraph), not the dedicated VPS assumed in CLAUDE.md §11. Consequently:

- **Postgres** and **Redis** run docker-internal only (no published host ports —
  5432/5433 and 6379/6380/6381 are already taken by other projects).
- The **backend** publishes on host port `8001` and the **frontend** on `3001`
  (defaults 8000/3000 are in use). See `BACKEND_HOST_PORT` / `FRONTEND_HOST_PORT`
  in `.env`.
- There is **no nginx container**; the existing **host nginx** reverse-proxies
  `leadkar.pk` to those ports (config to be added in Phase 8).

These adaptations are pending Nayyer's sign-off — see the open questions raised
during Phase 0 assessment.

## Status

**Phase 0 — Documentation & Scaffolding.** No application code yet. See CLAUDE.md §9
for the phase plan and acceptance criteria.
