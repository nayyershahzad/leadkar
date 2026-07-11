# LeadKar — Lead-Generation Cheat Sheet

> Working reference distilled from a multi-source research sweep (competitor products,
> B2B data schemas, scoring models, enrichment/verification, Google-Maps intent signals,
> marketplace pricing & compliance — 2025–2026 sources, cited at the end).
> Everything here is mapped to LeadKar's actual stack (`normalize.py`, planned
> `scoring.py`, exporters, packs/quoting). Companion to `wow_factor.docx`.
>
> **Golden rule (from CLAUDE.md §15.2):** the app computes every price, count, score, and
> tag **server-side**. The LLM only phrases. Nothing here changes that.

---

## 0. TL;DR — where LeadKar plays and how to win

- **The wedge is real.** Every incumbent — ZoomInfo, Apollo, Lusha, Cognism, RocketReach,
  Seamless — is US/NA-centric and weak on Pakistan/emerging-market data. LeadKar's
  Apify-sourced PKR model competes with **Outscraper / Apify actors on cost**, *not* with
  verified-contact databases on depth. Don't try to out-ZoomInfo ZoomInfo.
- **The industry's three chronic complaints** are your marketing copy: (1) **accuracy
  inflation** (advertised 97% vs real ~65–85% bounce-heavy), (2) **opaque / lock-in
  pricing** with auto-renewal traps, (3) **credit/endpoint cost-stacking**. LeadKar's flat
  PKR pricing, one-time packs (no credit expiry), and guaranteed-minimum quoting directly
  counter all three.
- **Most "wow" is free.** The compass actor already returns far more than `normalize.py`
  maps today. Lead scoring, signal tags, a WhatsApp flag, and richer fields are **pure
  backend code, zero extra Apify spend** — build these first (wow_factor Wave 1).
- **The premium fields that actually move buyers:** verified email *status*, a real
  mobile, and (uniquely valuable in PK) **WhatsApp reachability**.

---

## 1. Competitive landscape (one-screen map)

| Tool | Core data | Enrichment edge | Pricing shape | Weakness LeadKar exploits |
|---|---|---|---|---|
| **ZoomInfo** | 400M+ contacts, best US mobile, intent, org charts | direct-dial + streaming intent | opaque ~$15–60K/yr, auto-renew lock-in | thin outside NA; enterprise price |
| **Apollo** | 275M contacts, all-in-one (data+sequencer+dialer) | email/phone + 65 filters | credit+seat, $49–119/user/mo | weak intl/phone; billing disputes |
| **Lusha** | 280M dials, strong NA email | phone type + DNC flag, confidence scores | credits (1=email, 10=phone) | weak EMEA/APAC |
| **Cognism** | phone-verified "Diamond Data" (~98%) | human-verified mobile, GDPR/DNC | quote ~$15–25K/yr | thin US-SMB; pricey |
| **RocketReach** | large DB, 100+ filters | email+phone via extension | seat, $69–207/mo | 75–85% email / 55–65% phone accuracy |
| **Seamless.ai** | 1.7B contacts | real-time verify, job-change | credits, hidden ~$99–475/mo | **billing/cancellation** is the #1 gripe |
| **Clay** | no own DB — orchestrates 100+ providers | **waterfall** enrichment, AI research | dual-credit, $134–446/mo | steep learning curve; cost unpredictable |
| **Outscraper** | GMaps, 120+ fields | add-on email/validator/phone endpoints | PAYG $3/1K → ~$9–14/1K enriched | advertised price 3–5× at checkout |
| **Apify `compass/crawler-google-places`** | GMaps, broadest fields incl. reviews/distribution/popular-times | contact enrichment **opt-in add-on** | from **$1.50/1K** places | ~120 results/query → grid queries needed |
| **Apify `lukaskrivka/google-maps-with-contact-details`** | same place data | email + socials enrichment **ON by default** | from **$2.10/1K** places | enrichment cost spikes on low-yield runs |

**What buyers reward / punish (across all tools):** they reward *accuracy that matches the
claim*, *coverage in their region*, *transparent pricing*, and *recourse when data is bad*.
They punish *stale data / bounces*, *opaque sourcing*, *credit burn on failed lookups*, and
*resold non-exclusive leads*. Design LeadKar to be the opposite of each punish-item.

*Sources: Apollo, ZoomInfo, Lusha, Cognism, RocketReach, Seamless, Clay, Outscraper docs +
G2/Cleanlist/Salesmotion/Warmly reviews — see §9.*

---

## 2. Canonical lead schema

### 2a. What LeadKar maps today (18 fields, `normalize.py`)
`name, category, address, city, phone, carrier, website, email, rating, reviews_count,
lat, lng, google_place_id, instagram, facebook, opening_hours, source, scraped_at`

### 2b. Free additions from the SAME compass actor (zero extra Apify spend)

| Add field | Actor source | Why it matters | Notes |
|---|---|---|---|
| `whatsapp` (bool/flag) | derive from `phone` (+92 3XX mobile) | **#1 PK wow field**; ~98% open vs ~21% email | flag-only, opt-in gated (see §5) |
| `price_range` | `price` (e.g. "$$") | spend-capacity segmentation | listing-level |
| `images_count` | `imagesCount` | profile activity / management proxy | listing-level |
| `permanently_closed` / `temporarily_closed` | `permanentlyClosed` / `temporarilyClosed` | **freshness — drop closed before sale** | listing-level |
| `claimed` (bool) | **`claimThisBusiness`** (⚠ inverted) | active-owner signal; agency-lead filter | `claimThisBusiness == true` ⇒ **unclaimed** |
| extra socials `twitter, youtube, tiktok, linkedin, pinterest` | `twitters[0]` … | richer SMB outreach surface | some gated behind contact enrichment |
| `reviews_distribution` | `reviewsDistribution` (1★–5★) | rare/premium quality signal | **needs `scrapePlaceDetailPage: true`** (cost) |
| `review_recency` | max `reviews[].publishedAtDate` | freshness/active-owner signal | **needs detail-page crawl** (cost) |
| `lead_score` (0–100) + `signal_tag` | computed (§4) | the headline differentiator | pure code |

> **⚠ Field-name correction (verified against the live actor page):** the claimed/verified
> boolean is **`claimThisBusiness`**, and it is **inverted** — `true` means the listing can
> still be claimed (**unclaimed**), `false` means already claimed. Earlier notes calling it
> `claimed` or "not exposed" are both wrong. Derive: `claimed = (claimThisBusiness == false)`.

### 2c. Premium / "wow" fields ranked (what buyers actually pay up for)
1. **Verified mobile number** — hardest to source, highest connect value.
2. **WhatsApp-reachable flag** — outsized value in PK; almost no Western DB carries it.
3. **Verified email + status** (valid / catch-all / risky) — it's the *status*, not the raw
   email, that buyers pay for.
4. **Decision-maker name + title + work email** — turns a company row into a contact.
5. Direct-dial (vs switchboard), technographics, org chart, funding/growth, job-change.

For a **Google-Maps lead specifically**, the standout free-ish differentiators are:
scraped **email**, **rating + review distribution**, **social handles**, **place_id** (dedup
key), and the **`claimed`** flag — all from the actor LeadKar already uses.

*Sources: UpLead, Salesmotion, Cleanlist, Demandbase, Apify actor page.*

---

## 3. Google-Maps signal → tag rules

Turn stored fields into tags. **Compound 3+ signals — never tag on rating+count alone.**

| Tag | Rule (fields) | US threshold | PK calibration note |
|---|---|---|---|
| `hidden_gem` / `growth_prospect` | high `rating` + low `reviews_count` (+ has `website`) | rating ≥ 4.7 & 5–20 reviews | scale review band **down** for PK |
| `new_or_small` | `reviews_count` | < 50 | likely < ~20 in PK |
| `established_smb` | `reviews_count` | 50–500 | likely ~15–150 in PK |
| `chain_franchise` | `reviews_count` | > 500 | likely > ~150 in PK |
| `sweet_spot` (active, not saturated) | `reviews_count` | 20–100 | recalibrate per city×vertical |
| `reputation_risk` / `needs_help` | `rating` low | ≤ 3.5 | — |
| `unclaimed` / `needs_gbp_setup` | `claimThisBusiness == true` | boolean | strong-but-imperfect (can be stale) |
| `responsive_owner` | owner responses present in `reviews[]` | any | needs detail-page crawl |
| `active_recent` vs `stale_dormant` | max `review publishedAtDate` | ≤ 30d / > 6–12mo | needs detail-page crawl |
| `no_website` / `has_website` | `website` null/present | — | `no_website` = web-design lead |
| exclude `closed` | `permanentlyClosed`/`temporarilyClosed` | **hard drop** | also `skipClosedPlaces: true` at scrape |

> **⚠ Critical PK calibration:** the 50/500 US bands are wrong for Pakistan. LeadKar's real
> Karachi DHA/Clifton restaurant scrape yielded ~136 leads with much lower review counts than
> US norms. **Compute bands per city×vertical from your own data** (percentiles), don't import
> US numbers. Store observed distributions in `lead_density_stats` (already in schema §15.8).

*Sources: NotiQ, Outscraper, CazaLead, LeadLu, Sterling Sky, Apify actor page.*

---

## 4. Lead scoring algorithm (LeadKar 100-pt)

**Key insight the generic models miss:** inside a single pack, every lead shares the same
city+vertical, so **"fit" is constant and useless for sorting within a pack.** Reallocate the
standard model's fit/behavior weight into the three axes you *can* vary per row:
**Contactability + Business quality + Digital maturity.** (Use fit only for *cross-pack* or
*custom-order relevance*, not intra-pack sorting.) This matches the wow_factor Wave-1 split.

### Recommended weights (starting hypothesis — calibrate, see below)

| Axis | Weight | Components (points) |
|---|---|---|
| **Contactability** | 40 | phone present & valid **15** · email present & non-generic **15** · website live **5** · any social **5** |
| **Business quality** | 35 | rating scaled `((rating-3)/2)*20` clamp 0–20 · log-scaled reviews `min(15, 5*log10(1+reviews_count))` |
| **Digital maturity** | 25 | website **10** · ≥1 active social **10** · opening-hours present **5** |
| **Negatives** | − | permanently/temporarily closed **−30** · no phone AND no email **−20** · duplicate `place_id` **−15** |

```
score = clamp(0, 100, contactability + business_quality + digital_maturity + negatives)
```
Then **sort each deliverable dataset by `lead_score` desc** so buyers see best-first.

### Signal tags (ship alongside the score)
`hidden_gem` (rating ≥ 4.3–4.7 & small review band) · `established` · `major_chain` ·
`new_unproven` · `unclaimed` · `no_website` · `whatsapp_reachable` (see §3 for rules).

### Validation checklist (don't ship an unvalidated score)
- [ ] **Rank-order / decile lift** — top tier ≈ ~2× the base rate on your proxy target.
- [ ] **Known-good vs junk separation** — hand-labeled good rows outscore known duds.
- [ ] **Bootstrap with a proxy target now** (no conversions yet): manual-QA "contactable &
      real" on a sample, or downstream **email bounce rate**. Swap in real conversion later.
- [ ] **Back-test with no look-ahead** — only score on capture-time fields.
- [ ] **Quarterly recalibration** against actual closed sample. Treat weights as hypotheses.

*Sources: Scalarly, Saber, Breadcrumbs, digitalapplied, RevEngine, Pedowitz.*

---

## 5. Enrichment & verification stack (cheapest-first)

**Tier the spend: free offline → free DIY → cheap paid only on survivors.**

| Tier | Do this | Cost | Notes |
|---|---|---|---|
| 1. Free offline | E.164 normalize (libphonenumber) + **PK prefix→carrier** table (already in §8) + email syntax/MX/role/disposable filter | $0 | PK carrier is derivable offline — paid lookup unnecessary |
| 2. Free DIY | scrape homepage + `/contact`/`/about`/`/team` for emails & socials (`enrich.py`) | $0 | ~**30–40%** email hit-rate; socials hit higher on PK SMBs |
| 3. Cheap paid | verify **only survivors**: Bouncer/DeBounce ~**$2/1K** email; Twilio Line-Type ~**$0.008**/phone if line-type needed | low | do this **before sale** so buyers inherit a clean list |

### Email status reference (what to keep/flag/drop)

| Status | Meaning | Action |
|---|---|---|
| Valid / deliverable | mailbox exists (SMTP `RCPT TO` accepts) | keep |
| Invalid | syntax/MX fail or hard bounce | drop |
| Catch-all / accept-all | domain accepts everything → can't confirm | flag "risky" |
| Disposable | throwaway domain | drop |
| Role-based (`info@`,`sales@`) | function not person | segment separately, don't discard |
| Unknown | timeout/greylist | retry; don't charge |

Full SMTP verification catches ~95–99% of bad addresses vs ~70–90% for syntax/MX-only.
Real-world verifier accuracy lands ~85–95% and **tools disagree on catch-alls** — don't
promise "100% verified".

### WhatsApp (the PK wow field) — **flag only, for now**
- ~98% open rate, ~80–88% read within 5 min, 83% of PK users open WhatsApp daily.
- In PK a normalized `+92 3XX` mobile is *usually* on WhatsApp but **not guaranteed** — ship
  it as `whatsapp_likely`, not "verified". Landline/VoIP ≈ never on WhatsApp (line-type
  pre-filter). Real per-number validation exists (CheckNumber.AI, Maytapi, Apify validator)
  but ties into deferred WeTarseel/Phase-2 work.
- **Compliance:** being on WhatsApp is **not consent**. Meta requires opt-in before
  messaging; cold bulk = number bans. Sell it as a data attribute, not a green light.

### Decision-maker enrichment — mostly skip for PK
Western DBs (ZoomInfo/Apollo/Clearbit) have **thin PK coverage** — the same gap LeadKar
exploits — so their decision-maker data hit-rates poorly here. DIY pattern-guess
(`first.last@domain`) + verify is the only viable route, and low-yield. Deprioritize.

*Sources: myemailverifier, bulkemailchecker, Instantly, ZeroBounce, Bouncer, DeBounce,
Twilio, intellicon, tyntec, cleanlist, scrapingbee.*

---

## 6. Packaging, pricing & trust mechanics

### Pricing reality check
- Western verified-contact benchmark is **~$0.40–0.60 per lead** (UpLead). LeadKar's ~PKR 6
  catalog / ~PKR 8 custom is an **order-of-magnitude discount** — that's the wedge, not a
  race to the bottom. Pre-built packs ≈ zero marginal cost → thin volume pricing is correct
  (aligns with CLAUDE.md §15.6).
- Charge custom orders on **verified/delivered** rows, not raw scraped rows (market norm;
  aligns with LeadKar's guaranteed-minimum quoting).
- One-time packs (no credit expiry) are a **marketable differentiator** vs the credit-burn
  incumbents — say so.

### Trust mechanics — build each into the pack page (checklist)
- [ ] **Published accuracy %** (leaders show 95–98%). Put a specific number on the page.
      *(Biggest current gap vs market.)*
- [ ] **Bounce replacement / credit-back policy** for bad emails. Single most reassuring
      signal for list buyers. *(Currently missing — add it.)*
- [ ] **Sample preview** — 3 real rows before purchase. ✅ already have `sample_preview`.
- [ ] **Freshness label** — surface `last_refreshed_at` on the card. ✅ field exists, surface it.
- [ ] **Per-pack quality summary** — e.g. "452 leads · 38% verified email · 41% WhatsApp ·
      22 hidden gems · refreshed Jun 2026". Doubles as a trust signal *and* the Wave-1 wow.
- [ ] **Transparent sourcing** — "public Google Maps business listings, factual fields only".
- [ ] **Exclusivity framing** — packs are shared off-the-shelf inventory (be upfront, price
      low); position **custom orders as exclusive**.

*Sources: UpLead, BookYourData, LimeLeads, Ascentrik, Wappalyzer, SmartBug, leadgen-economy.*

---

## 7. Data quality, deliverability & compliance checklist

**Quality pipeline (scrape → sale):**
- [ ] **Dedup** on `google_place_id` (primary) / website domain — target dup rate < 2%.
- [ ] **Drop permanently/temporarily closed** post-fetch (plus `skipClosedPlaces: true`).
- [ ] **Refresh cadence:** B2B data decays ~70%/yr. Quarterly `CATALOG_REFRESH_CRON` is the
      *floor*; re-verify emails/phones every 1–3 months for high-value packs.
- [ ] **Verify before sale** (email pass + phone normalize + completeness score).
- [ ] **Track per-pack:** completeness, email-valid %, phone-present %, dup rate, freshness.

**Deliverability guidance to ship *with* each delivery** (protects buyers → protects you from
"your data bounced" disputes that are actually cold-domain problems):
- Warm up new domains (5–10/day, ramp over 4–6 wks); authenticate **SPF + DKIM + DMARC** +
  one-click unsubscribe; re-verify before each send. Gmail/Yahoo bulk rules require
  **bounces < ~2%, spam complaints < 0.3%** — seller-side verification directly protects this.
- Set honest coverage expectations: label which rows have a deliverable email (~30–40%), not
  "every row".

**Compliance posture (practical flags — not legal advice):**
- Scraping **public, factual** business data (name/address/phone/coords) is defensible —
  facts aren't copyrightable; *hiQ v. LinkedIn* (9th Cir.) held scraping public data doesn't
  violate the CFAA. **Do NOT republish reviews/photos/descriptions** (copyrighted
  expression) and don't defeat access controls (CAPTCHA/anti-bot).
- It's **business (not consumer) data** → materially lower risk. State this plainly.
- GDPR exposure is low (PK-focused) but if EU contacts appear, B2B relies on **legitimate
  interest** + transparent sourcing + opt-out. CAN-SPAM (US buyers) has **no B2B exemption** —
  give buyers a short compliance note (accurate headers, physical address, working opt-out).
- **Public stance to publish:** "public business listings only · factual fields · no
  reviews/photos republished · business not consumer data · opt-out honored." Cheap trust win.

*Sources: Derrick, Bitscale, Instantly, FTC, Unify GTM, Scrap.io, MapScraping, hiQ explainers.*

---

## 8. Mapping to LeadKar's build (what to do, where)

| Area | Status | Action | Where | Spend |
|---|---|---|---|---|
| Lead score + tags | ❌ not built | build `compute_lead_score(row)` + `signal_tags(row)`; sort dataset desc | **NEW** `app/services/scoring.py` | $0 |
| Richer free fields | ❌ | extend `CANONICAL_FIELDS` + `normalize_place`: `whatsapp`, `price_range`, `images_count`, `permanently/temporarily_closed`, `claimed` (from `claimThisBusiness`, inverted), extra socials, `lead_score`, `signal_tag` | `integrations/normalize.py` | $0 |
| Exporters | ❌ | new columns in canonical order; XLSX highlight the score column | `integrations/exporters.py` | $0 |
| Pack aggregates | ❌ | "Avg LeadScore · % WhatsApp · N hidden gems · freshness" into `sample_preview` JSONB (no migration) + card | `packs` + `PackCard.tsx` | $0 |
| PK band calibration | ❌ | compute review bands per city×vertical from own data | `lead_density_stats` (exists) | $0 |
| Cheap verify-before-sale | ⚠ partial | run survivor emails through Bouncer/DeBounce (~$2/1K) pre-delivery | `tasks/enrich.py` | low, **needs spend OK** |
| Detail-page signals | ❌ | `reviewsDistribution`, review recency, owner-response → richer tags | Apify input `scrapePlaceDetailPage:true` | **needs spend OK** |
| Contact-enrichment actor | ❌ | evaluate `lukaskrivka/...contact-details` for emails/socials by default | — | **actor switch → Nayyer sign-off (CLAUDE.md §8)** |
| Trust page items | ⚠ partial | publish accuracy % + bounce-replacement policy; surface freshness + quality summary | frontend | $0 |

**Build order (from wow_factor.docx, confirmed by this research):**
- 🟢 **Wave 1 (now, $0):** scoring.py + normalize richer fields + WhatsApp flag + exporters +
  pack aggregates. Backfill over the 136 Karachi leads → instant demo-able wow.
- 🟡 **Wave 2 (needs spend OK):** `min_rating`/review-band filter in `build_gmaps_input`;
  "Hidden Gems" pack archetype; high-ticket PK packs (Sialkot surgical/sports exporters, IT
  services, logistics/3PL, private hospitals). Requires `--dry-run` cost print + approval.
- 🔵 **Wave 3 (Nayyer approval):** evaluate contact-details actor (LinkedIn + verified email
  + decision-maker) — biggest raw wow but an **actor switch (CLAUDE.md §8)**; optional email
  verification add-on; real WhatsApp validation (Phase-2/WeTarseel).

---

## 9. Sources

**Competitors:** apollo.io · zoominfo.com · lusha.com/docs · cognism.com · rocketreach (G2) ·
seamless.ai (G2) · clay.com · outscraper.com · apify.com/compass/crawler-google-places ·
apify.com/lukaskrivka/google-maps-with-contact-details · cleanlist.ai · salesmotion.io ·
warmly.ai · igleads.io · scalelist.com.
**Schema:** uplead.com/apollo-vs-zoominfo · salesmotion.io · cleanlist.ai · demandbase.com ·
zapier.com · Apify actor page.
**Scoring:** scalarly.com · saber.app (firmographic + data-quality) · breadcrumbs.io ·
digitalapplied.com · syncgtm.com · revengine.substack.com · pedowitzgroup.com.
**Enrichment/verify:** myemailverifier.com · bulkemailchecker.com · mailtester.ninja ·
instantly.ai · zerobounce.net · usebouncer.com · sprout24.com (DeBounce) · hunter.io ·
twilio.com/lookup · abstractapi.com · checknumber.ai · maytapi · intellicon.io · tyntec.com ·
green-api.com · scrapingbee.com · octoparse.com.
**Maps signals:** notiq.io · outscraper.com (qualify-leads + Medium guide) · cazalead.com ·
leadlu.com · leadsagent.io · leads-sniper.com · scrap.io · stevesie.com · sterlingsky.ca ·
clientstudio.com · wiserreview.com.
**Pricing/compliance:** uplead.com/pricing · bookyourdata.com · limeleads.com ·
ascentrik.com · wappalyzer.com · dwmedia.com · px.com · smartbugmedia.com · leadempire.us ·
leadgen-economy.com · instantly.ai (deliverability/warmup/compliance) · thedigitalbloom.com ·
mailpool.ai · topo.io · ftc.gov (CAN-SPAM) · unifygtm.com · scrap.io · mapscraping.com ·
iblead.com · derrick-app.com · bitscale.ai · crustdata.com.

*Compiled 2026-07-07 from 6 parallel research agents + direct verification of the compass
actor's `claimThisBusiness` field. Numeric thresholds are US-market starting points — the
⚠ PK-calibration notes are load-bearing; recompute bands from LeadKar's own data.*
