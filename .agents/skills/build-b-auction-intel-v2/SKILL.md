---
name: build-b-auction-intel-v2
description: Runbook for Build B (Auction Intelligence v2) read-only modules — B1 Manifest ROI Analyser, B2 HiBid Churn Tracker, B3 Fail-Closed NC Land Parcel Scorer, and strictly isolated B4 Kia Carnival Checker.
---

# Skill Runbook: Build B — Auction Intelligence v2

**Owner:** Temitope Soneye (`Tosson Services LLC dba Tosson Environmental Analytics`)  
**Environment:** `/home/antigravity/.venv/bin/python` (Python 3.12; `Pillow==13.0.0`, `requests==2.34.2`, `beautifulsoup4==4.15.0`, `PyYAML==6.0.4`, `jsonschema==4.26.0`, `pytest==9.2.0`)

## Standing Safety Rules
1. **Strictly read-only:** Never bid, purchase, send messages, create accounts, or modify live `auctions.tossonanalytics.com` files/behavior.
2. **No secrets in repo:** Reference environment variable NAMES only (`auction-intel-v2/.env.example`).
3. **B4 strict isolation:** Never import `kia_carnival` from `manifest_roi`, `hibid_churn`, or `land_scorer` (or vice versa), and never bundle B4 into general auction cron jobs.
4. **C-3 notice:** B4's Summer-2027 KFA finance-clause stub is a **DOCUMENT CHECKLIST GENERATOR ONLY — NOT LEGAL OR FINANCIAL ADVICE**.
5. **Fixtures independence:** All tests pass with zero `/home/antigravity/fixtures/` directory present using synthetic fixtures in `tests/fixtures_synthetic/build_b/`.

## 1. Run B1 — Manifest ROI Analyser

```bash
# Public-comp fallback mode (when no sold-history CSV is staged)
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m manifest_roi \
  --manifest tests/fixtures_synthetic/build_b/liquidation_com_sample.csv \
  --format auto \
  --out-md auction-intel-v2/reports/sample_manifest_roi_report.md \
  --out-json auction-intel-v2/reports/sample_manifest_roi_report.json

# Owner sold-history / hybrid mode (pass --sold-history <path>)
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m manifest_roi \
  --manifest /path/to/manifest.csv \
  --sold-history /path/to/sold-history.csv \
  --out-md /tmp/roi.md --out-json /tmp/roi.json
```

**Verify:** Confirm active comp mode (`PUBLIC_COMP_FALLBACK`, `OWNER_SOLD_HISTORY`, or `HYBRID`) appears in both Markdown and JSON headers, and hand-check `landed_cost`, `selling_fees`, `net_resale_mid`, `net_profit`, `roi_pct`, and `verdict`.

## 2. Run B2 — HiBid Churn Tracker

```bash
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m hibid_churn \
  --prev tests/fixtures_synthetic/build_b/hibid_prev.json \
  --curr tests/fixtures_synthetic/build_b/hibid_curr.json \
  --categories Tools \
  --out-md auction-intel-v2/reports/sample_hibid_churn_report.md \
  --out-json auction-intel-v2/reports/sample_hibid_churn_report.json
```

**Verify:** Confirm planted re-listed lot appears under `RELISTED` with `match_method: "TITLE_AND_IMAGE"`, title similarity, and Pillow dHash Hamming distance (`<= 10` bits).

## 3. Run B3 — Fail-Closed NC Land Parcel Scorer

```bash
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m land_scorer \
  --input tests/fixtures_synthetic/build_b/land_parcels_sample.json \
  --out-md auction-intel-v2/reports/sample_land_scorer_report.md \
  --out-json auction-intel-v2/reports/sample_land_scorer_report.json
```

**Verify:**
- Only NC parcels in Caswell, Rockingham, or Person counties with `1.0 <= acreage <= 5.0` and `price < $30,000` appear in `passing_parcels`.
- Parcels with `price <= $5,000` carry `primary_track: "AUCTION_TRACK"`.
- Missing/invalid price or acreage records appear in `excluded_summary` and NEVER in `passing_parcels`.
- Every emitted `url` is either a validated direct URL or literal `"URL not captured"` (never a search-results URL).

## 4. Run B4 — Isolated Kia Carnival Checker (Standalone)

```bash
# Live NHTSA vPIC + Recalls lookup (monitor mode only)
PYTHONPATH=/home/antigravity/auction-intel-v2 \
/home/antigravity/.venv/bin/python -m kia_carnival \
  --input /path/to/kia_listings.json \
  --contract-text /path/to/optional_contract.txt \
  --out-md /tmp/kia_report.md \
  --out-json /tmp/kia_report.json
```

**Verify:**
- VIP Lounge / SX Prestige trims emit `FLAGGED_OUT_VIP_LOUNGE`.
- Open SC266 / `23V144000` VINs emit `SC266_OPEN` and `FLAG_RECALL_SC266_OPEN`, always with direct link `https://www.nhtsa.gov/recalls?vin=<VIN>`.
- Finance checklist includes banner `DOCUMENT CHECKLIST GENERATOR ONLY — NOT LEGAL OR FINANCIAL ADVICE`.

## 5. Run Full Build B Verification Suite

```bash
/home/antigravity/.venv/bin/pytest tests/test_build_b_*.py
```
