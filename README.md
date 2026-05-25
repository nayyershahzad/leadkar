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
- The **backend** publishes on host port `8002` and the **frontend** on `3002`
  (8000/8001 and 3000/3001 are all in use by other projects). See
  `BACKEND_HOST_PORT` / `FRONTEND_HOST_PORT` in `.env`.
- There is **no nginx container**; the existing **host nginx** reverse-proxies
  `leadkar.pk` to those ports (config to be added in Phase 8).

These adaptations are pending Nayyer's sign-off — see the open questions raised
during Phase 0 assessment.

## Status

**Phase 1 — Infra & Database (complete).** Docker Compose runs postgres, redis,
backend (FastAPI `/health`), worker, and beat; Alembic `0001_initial` applies the
full §6 schema. See CLAUDE.md §9 for the phase plan and acceptance criteria.

### Local operations

```bash
docker compose up -d                                   # start the stack
curl http://127.0.0.1:8002/health                      # -> {"status":"ok"}
docker compose exec backend alembic upgrade head       # apply migrations
docker compose exec backend celery -A app.tasks.celery_app inspect ping
```
