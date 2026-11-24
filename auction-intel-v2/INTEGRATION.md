# Auction Intelligence v2 — Non-Invasive Integration Guide (B5)

- **Owner:** Temitope Soneye (`Tosson Services LLC dba Tosson Environmental Analytics`)
- **Live Target Observed (Read-Only):** `auctions.tossonanalytics.com` (Mon/Wed/Fri refresh + closing-`<48h` alert cadence)
- **Safety Posture:** **READ-ONLY ANALYSIS ONLY.** Zero bids, zero purchases, zero account changes, zero account creation, zero outgoing messages, and **zero modifications** to existing live dashboard code, webroot, or database state.

---

## 1. Sidecar Architecture (Zero-Touch on Live Dashboard)

Build B operates strictly as a **downstream read-only sidecar** consuming existing snapshot exports and writing its own Markdown/JSON artifacts to a separate directory (`$AUCTION_INTEL_V2_OUTPUT_DIR`):

```text
Existing Live Pipeline (UNMODIFIED)
  ├── Mon/Wed/Fri refresh scraper ──▶ $AUCTION_INTEL_SNAPSHOT_DIR/hibid_<YYYYMMDD>.json (read-only input)
  └── Closing-<48h alert watcher  ──▶ live dashboard + existing alert channel (unchanged)
                                         │
                                         │ (read-only file reads ONLY)
                                         ▼
Auction Intelligence v2 Sidecar (SEPARATE output dir: $AUCTION_INTEL_V2_OUTPUT_DIR)
  ├── B1 Manifest ROI Analyser    ──▶ reports/manifest_roi_<YYYYMMDD>.{md,json}
  ├── B2 HiBid Churn Tracker      ──▶ reports/hibid_churn_<YYYYMMDD>.{md,json}
  └── B3 NC Land Parcel Scorer    ──▶ reports/land_scorer_<YYYYMMDD>.{md,json}

STRICTLY SEPARATE — NEVER BUNDLED INTO GENERAL AUCTION BATCH:
  └── B4 Kia Carnival Checker     ──▶ $KIA_CARNIVAL_MONITOR_OUTPUT_DIR/kia_carnival_<YYYYMMDD>.{md,json}
```

### Non-Negotiable Isolation Boundaries
1. **Live dashboard untouched:** Neither B1, B2, B3, nor B4 writes into the live webroot or modifies any live scraper cron job.
2. **Environment variable NAMES only:** See [`.env.example`](.env.example) for required variable names. Never store credential values or tokens in this repository.
3. **B4 strict separation:** `kia_carnival/` has **zero Python imports** to or from `manifest_roi/`, `hibid_churn/`, or `land_scorer/` (enforced by AST test in `tests/test_build_b_kia_carnival.py`). It runs on its own standalone weekly monitor timer and writes to its own `$KIA_CARNIVAL_MONITOR_OUTPUT_DIR`.

---

## 2. Mon / Wed / Fri Refresh Sidecar Hooks

After the existing Mon/Wed/Fri refresh writes the latest HiBid snapshot file, run B2 (and optionally B1 if new manifests are staged, and B3 for public county feeds) as a post-refresh sidecar:

### 2.1 Snapshot Field Mapping (Drop-In Compatibility)
B2 natively expects canonical fields `lot_id, title, category, current_bid, url, image_path, snapshot_ts` and automatically recognizes common aliases (`lotId`, `highBid`, `lotUrl`, `captured_at`). If the existing scraper uses custom column names, pass `--field-map /path/to/field_map.yaml`:

```yaml
# Example external field_map.yaml (no live scraper changes needed)
lot_id: LotNumber
title: LeadTitle
category: CategoryName
current_bid: HighBidAmount
url: LotDetailUrl
image_path: LocalThumbnailPath
snapshot_ts: ScrapedAtUtc
```

### 2.2 Sidecar Commands (Venv-Isolated `.venv/bin/python`)

```bash
# 1. B2 — HiBid Churn Tracker (compares previous vs current Mon/Wed/Fri snapshot)
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m hibid_churn \
  --prev "${AUCTION_INTEL_SNAPSHOT_DIR}/hibid_prev.json" \
  --curr "${AUCTION_INTEL_SNAPSHOT_DIR}/hibid_curr.json" \
  --image-dir "${AUCTION_INTEL_HIBID_IMAGE_DIR}" \
  --categories "Tools,Equipment,Electronics" \
  --out-md "${AUCTION_INTEL_V2_OUTPUT_DIR}/hibid_churn_latest.md" \
  --out-json "${AUCTION_INTEL_V2_OUTPUT_DIR}/hibid_churn_latest.json"

# 2. B1 — Manifest ROI Analyser (run whenever Liquidation.com or B-Stock CSV is staged)
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m manifest_roi \
  --manifest "${AUCTION_INTEL_MANIFEST_DIR}/latest_manifest.csv" \
  --format auto \
  --sold-history "${AUCTION_INTEL_SOLD_HISTORY_CSV}" \
  --out-md "${AUCTION_INTEL_V2_OUTPUT_DIR}/manifest_roi_latest.md" \
  --out-json "${AUCTION_INTEL_V2_OUTPUT_DIR}/manifest_roi_latest.json"

# 3. B3 — NC Land Parcel Scorer (fail-closed, direct-URL enforced)
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m land_scorer \
  --input "${AUCTION_INTEL_SNAPSHOT_DIR}/nc_land_candidates.json" \
  --out-md "${AUCTION_INTEL_V2_OUTPUT_DIR}/land_scorer_latest.md" \
  --out-json "${AUCTION_INTEL_V2_OUTPUT_DIR}/land_scorer_latest.json"
```

*(Omit `--sold-history` in B1 when owner sold history is unavailable; B1 will cleanly switch to `PUBLIC_COMP_FALLBACK` mode and print the active mode in both JSON and Markdown headers.)*

---

## 3. Closing-`<48h` Ping Sidecar Enrichment

The existing closing-`<48h` ping continues running unchanged. To enrich your review of lots closing within 48 hours without touching the alert sender:

1. Run B2 against the latest snapshot and inspect `relisted` and `price_down` arrays in `hibid_churn_latest.json`:
   - A closing-`<48h` lot flagged `RELISTED` indicates prior cycle unsold inventory (useful context before setting a manual ceiling).
   - A lot flagged `PRICE_DOWN` or `UNCHANGED` signals low competitive bid velocity.
2. For any Liquidation.com / B-Stock lot closing within 48 hours, run B1 with `--bid-price <current_bid>` to check whether the current bid still clears the `STRONG` (`ROI >= 40%` and `net_profit >= $150`) or `MARGINAL` (`15% <= ROI < 40%` and `net_profit > $0`) band.
3. For NC county tax-auction parcels closing within 48 hours, review B3's `AUCTION_TRACK` (`<= $5,000`) ranked rows and open each parcel's validated direct URL (or note literal `"URL not captured"` for manual GIS lookup).

---

## 4. Cron & Systemd Sidecar Templates (EliteDesk Linux Mint)

### Cron Example (Mon/Wed/Fri at 07:30 local, 30 min after live refresh)
```cron
# Auction Intelligence v2 sidecar (read-only — separate from live auctions.tossonanalytics.com)
30 7 * * 1,3,5 . /path/to/local.env && PYTHONPATH=/home/antigravity/auction-intel-v2 /home/antigravity/.venv/bin/python -m hibid_churn --prev "$AUCTION_INTEL_SNAPSHOT_DIR/prev.json" --curr "$AUCTION_INTEL_SNAPSHOT_DIR/curr.json" --out-md "$AUCTION_INTEL_V2_OUTPUT_DIR/hibid_churn_$(date +\%F).md" --out-json "$AUCTION_INTEL_V2_OUTPUT_DIR/hibid_churn_$(date +\%F).json"
```

### Systemd User Timer Example (Optional Alternative)
```ini
# ~/.config/systemd/user/auction-intel-v2-churn.service
[Unit]
Description=Auction Intelligence v2 HiBid Churn Sidecar (Read-Only)

[Service]
Type=oneshot
EnvironmentFile=%h/.config/auction-intel-v2.env
Environment=PYTHONPATH=/home/antigravity/auction-intel-v2
ExecStart=/home/antigravity/.venv/bin/python -m hibid_churn --prev ${AUCTION_INTEL_SNAPSHOT_DIR}/prev.json --curr ${AUCTION_INTEL_SNAPSHOT_DIR}/curr.json --out-md ${AUCTION_INTEL_V2_OUTPUT_DIR}/hibid_churn_latest.md --out-json ${AUCTION_INTEL_V2_OUTPUT_DIR}/hibid_churn_latest.json
```

---

## 5. B4 — Kia Carnival Checker (Standalone Schedule Only)

**NEVER merge B4 into the Mon/Wed/Fri general auction batch.**

- Runs on an independent weekly monitor schedule (e.g., Sunday 09:00 local) or manually on demand when reviewing candidate 2022+ Kia Carnival listings.
- Uses public domain NHTSA vPIC (`https://vpic.nhtsa.dot.gov/api/`) and NHTSA Recalls (`https://api.nhtsa.gov/recalls/recallsByVehicle`) APIs (read-only GET).
- Includes the Summer-2027 KFA finance-clause scanner stub, explicitly labelled **DOCUMENT CHECKLIST GENERATOR ONLY — NOT LEGAL OR FINANCIAL ADVICE**.

```bash
# Standalone B4 invocation (Monitor Mode Only)
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m kia_carnival \
  --input /path/to/carnival_candidates.json \
  --out-md "${KIA_CARNIVAL_MONITOR_OUTPUT_DIR}/kia_carnival_report.md" \
  --out-json "${KIA_CARNIVAL_MONITOR_OUTPUT_DIR}/kia_carnival_report.json"
```
