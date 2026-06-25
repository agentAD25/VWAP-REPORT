# 6EZ24 30m VWAP Report — Public Historical Sample

**View-only static sample** for review. Not a live market data product.

## Scope

| Field | Value |
|-------|--------|
| Contract | 6EZ24 |
| Timeframe | 30m RTH bar-close lattice |
| Session window | 2024-09-18 through 2024-12-10 (calendar) |
| Complete RTH sessions | 48 (whitelist-certified when applicable) |
| Bar lattice | 13 closes per session, 09:35–16:00 ET |

## What is included

- Static HTML dashboards under `dashboards/` (including `dashboards/index.html`)
- **Gallery thumbnails are static PNG previews** of each dashboard page (no downloadable data)
- Embedded charts and tables rendered in HTML only

## What is **not** included (by design)

- No CSV, JSON, Parquet, or API/chart-data downloads
- No `report_params.json`, bridge manifests, or internal audit artifacts
- No raw bar lattices or `vwap_events` machine-readable extracts
- No real-time quotes or execution feeds
- **Public machine-readable exports are blocked** (`machine_readable_exports`: internal only)

## Lineage

- Generated from internal canonical parquet/report research bundle: `D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_strategy_research\6e_discovered_full_sweep_20260625\6EZ24`
- Packaged from internal regen bundle: `D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports_internal_regen\6e_discovered_bridge_20260625\6EZ24_20240918-20241210_30m`
- Upstream **1-minute bar regression gate:** `ONE_MINUTE_BAR_ISSUE_FIXED_CONFIRMED`
- `public_export`: **false**

## Usage

Open `dashboards/index.html` in a browser (file:// or static host). Links are relative within this folder.

## Not deployed

This folder is **not** synced to GitHub Pages unless explicitly approved after operator review.
