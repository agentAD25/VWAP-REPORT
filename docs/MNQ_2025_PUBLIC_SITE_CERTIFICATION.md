# MNQ 2025 Public VWAP Report Certification

**Date:** 2026-05-21  
**Final decision label:** `MNQ_2025_FINAL_PUBLIC_CERTIFICATION_PASS`  
**Public site:** [https://agentad25.github.io/VWAP-REPORT/](https://agentad25.github.io/VWAP-REPORT/)

This memo records the completed MNQ 2025 public gallery rollout and the final live certification result. It is operator documentation only; it does not change report data, manifest routing, or any certified HTML/PNG assets.

---

## Certified coverage

| Contract | Date range | Certified timeframes | Status |
|----------|------------|----------------------|--------|
| MNQZ25 | 20250914-20251212 | 1m, 5m, 15m, 30m | LIVE_PUBLIC_CERTIFIED |
| MNQH25 | 20241216-20250314 | 1m, 5m, 15m, 30m | LIVE_PUBLIC_CERTIFIED |
| MNQM25 | 20250317-20250613 | 1m, 5m, 15m, 30m | LIVE_PUBLIC_CERTIFIED |
| MNQU25 | 20250616-20250912 | 1m, 5m, 15m, 30m | LIVE_PUBLIC_CERTIFIED |

**Matrix size:** 16 certified reports (4 contracts × 4 timeframes).

Each certified entry uses:

- `status: CURRENT_CERTIFIED_PUBLIC`
- `active: true`, `canonical: true`, `public_safe: true`
- `csv: []` (no public data exports in manifest)
- `dashboard_index: reports/{CONTRACT}_{START}-{END}_{TF}/dashboards/index.html`

Per report, the public surface includes:

- 1 dashboard index (`dashboards/index.html`)
- 9 CORE_PUBLIC dashboard pages
- 9 PNG index previews (no placeholders)

---

## Certification gates passed

Final live certification (2026-05-21) verified all gates below for every certified report.

| Gate | Scope | Result |
|------|--------|--------|
| Manifest gate | 16 entries in live `manifest.json` | Pass |
| Dashboard index gate | 16 `dashboards/index.html` pages | Pass |
| Individual dashboard page gate | 144 CORE_PUBLIC HTML pages (16 × 9) | Pass |
| Hold/fail KPI gate | 16 `hold_fail_rates` pages | Pass |
| Hold/fail thumbnail gate | 16 index card PNG previews | Pass |
| Visual parity gate | Dark ALPHA DRIP shell; no BOM/default white/serif layout | Pass |
| Query-route gate | `?contract=&tf=` and `?contract=&timeframe=` (Playwright) | Pass |
| Legacy-route gate | Wrong-date root indexes and `vwap_events` paths | Pass (404 or inactive) |
| Public-safety gate | No machine-readable exports in public folders | Pass |

**CORE_PUBLIC dashboard stems (9 per report):**

- `daily_max_extensions`
- `dashboard_all_events`
- `dashboard_crosses`
- `extension_tail_metrics`
- `heatmap_time_of_day_x_reaction`
- `hold_fail_rates`
- `mfe_mae_by_event_window`
- `oos_by_month`
- `regime_segment_grid`

---

## Rollout and fix history (summary)

### Data and lattice readiness

- **1m open-lattice gate** confirmed for MNQ 2025 certification scope.
- **Derived 5m / 15m / 30m lattices** confirmed from the 1m foundation.

### Public packaging lifecycle

- Public reports use the **`dashboards/index.html`** entry point (not legacy report-root indexes).
- Manifest entries use **`CURRENT_CERTIFIED_PUBLIC`** with **`csv: []`**.
- Legacy wrong-date routes (e.g. `20241215`, `20250316`, `20250615`) and report-root / `vwap_events` paths are removed or return **404**.

### Visual and UX fixes (VWAP-REPORT)

| Commit | Summary |
|--------|---------|
| `a9e32c6` | Dashboard index visual parity (BOM-safe themed shell) |
| `ed0534e` | Individual dashboard page visual parity (144 pages) |
| `a710ab8` | Hold/fail small-sample KPI labels (`n=`), warnings, thumbnail refresh |

### Report additions (VWAP-REPORT)

| Commit | Summary |
|--------|---------|
| `4702b7b` | Certified MNQZ25 1m |
| `03688c4` | Certified MNQZ25 15m |
| `c69747e` | Certified MNQZ25 30m |
| `06de5d6` | Certified MNQM25 (all TFs) |
| `b5bd94c` | Certified MNQU25 (all TFs) |
| (prior) | MNQH25 certified reports and MNQZ25 5m |

### Source guardrails (supabase-opti-database `main`)

| Commit | Summary |
|--------|---------|
| `bf990f4` | Public report lifecycle documentation; index BOM-safe theme loading |
| `fbbd141` | `normalize_dashboard_page_html()` — strip BOM, inject disclosure CSS on CORE_PUBLIC pages |
| `9122dd1` | Hold/fail KPI sample-size labels and low-n warnings in builder/registry |

These source changes ensure future public packaging emits normalized, disclosure-aware HTML without altering certified public rate values retroactively.

---

## Public-safety statement

Certified public content is **research output only**:

- **No public CSV exports** — manifest `csv: []` for all 16 certified entries.
- **No public JSON, parquet, API, or chart-data exports** in certified report folders or page links.
- **`manifest.json`** is metadata for gallery routing only.
- Pages include **historical RTH VWAP research disclosure** (not real-time market data; not an execution feed).
- Raw OHLCV lattices, NinjaTrader certification bundles, and internal audit artifacts are **not** published.

---

## Query-route caveat

Gallery deep links use **client-side JavaScript** (`app.js` loads `manifest.json` and routes by contract/timeframe).

- **HTTP-only fetch** of `/?contract=MNQM25&tf=15m` may return the gallery shell HTML; that is expected.
- **Playwright/browser routing** confirmed redirect to the correct `dashboards/index.html` for all 16 certified contract/timeframe pairs (both `tf` and `timeframe` query parameters).

---

## Hold/fail interpretation note

Hold and fail rates are **mathematically correct** at the bucket level:

- `hold_rate = held_count / total_events`
- `fail_rate = failed_count / total_events`
- `held_count` and `failed_count` are **not** required to sum to `total_events` (some events are neither held nor failed).

**100% / 0% extremes** often appear in **low-n TOUCH/PIERCE buckets** on 15m and 30m timeframes. Public pages now display:

- **`n=`** on Highest Hold Rate and Highest Fail Rate KPI cards
- **Small-sample warnings** when the leading KPI bucket has `total_events < 10`
- Full **Data Preview** table rows (no rows hidden)

Example verified live: [MNQM25 15m hold/fail](https://agentad25.github.io/VWAP-REPORT/reports/MNQM25_20250317-20250613_15m/dashboards/MNQM25_20250317-20250613_15m_hold_fail_rates.html).

---

## Closeout

**MNQ 2025 public report rollout is complete** for the 16-report certified matrix on GitHub Pages.

Operators may use this site as the canonical public gallery for MNQZ25, MNQH25, MNQM25, and MNQU25 VWAP research dashboards across 1m, 5m, 15m, and 30m timeframes.

**Certification artifact (local audit, not published):** `out/audits/final_mnq_2025_certification.json` (generated during final certification rerun).

---

*Document version: 2026-05-21 · Label: `MNQ_2025_FINAL_PUBLIC_CERTIFICATION_PASS`*
