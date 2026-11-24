# Auction Intelligence v2 (Build B)

**Owner:** Temitope Soneye (`Tosson Services LLC dba Tosson Environmental Analytics`)  
**Mode:** Strictly Read-Only Analysis (zero bidding, zero purchasing, zero account creation, zero live dashboard mutations)

## Modules

| Module | Directory | Purpose | Sample Verified Report |
|---|---|---|---|
| **B1** | `manifest_roi/` | Liquidation.com & B-Stock CSV parser, landed-cost & resale-comp ROI engine (`OWNER_SOLD_HISTORY` / `HYBRID` / `PUBLIC_COMP_FALLBACK`), verdict bands (`STRONG` / `MARGINAL` / `PASS`) | [`reports/sample_manifest_roi_report.md`](reports/sample_manifest_roi_report.md) |
| **B2** | `hibid_churn/` | Snapshot diff across refresh cycles, re-list detection via normalized title similarity + Pillow 64-bit dHash, price delta tracking (`NEW`, `RELISTED`, `PRICE_UP`, `PRICE_DOWN`, `UNCHANGED`, `DROPPED`) | [`reports/sample_hibid_churn_report.md`](reports/sample_hibid_churn_report.md) |
| **B3** | `land_scorer/` | Fail-closed NC land parcel scorer (`Caswell`, `Rockingham`, `Person`; `1.0–5.0` acres; cash `< $30k`, auction `<= $5k`; Mebane NC distance) enforcing direct URLs or literal `"URL not captured"` | [`reports/sample_land_scorer_report.md`](reports/sample_land_scorer_report.md) |
| **B4** | `kia_carnival/` | **STRICTLY SEPARATE** 2022+ Kia Carnival monitor (NHTSA vPIC VIN decode, SC266 / `23V144000` recall check, EX/SX vs VIP Lounge trim filter, Summer-2027 KFA finance-clause checklist stub — **document checklist generator only, not legal or financial advice**) | [`reports/sample_kia_carnival_report.md`](reports/sample_kia_carnival_report.md) |
| **B5** | `INTEGRATION.md` | Non-invasive Mon/Wed/Fri and closing-`<48h` sidecar integration notes for `auctions.tossonanalytics.com` | [`INTEGRATION.md`](INTEGRATION.md) |

## Quick Verification (Offline, No `fixtures/` Required)

```bash
/home/antigravity/.venv/bin/pytest tests/test_build_b_*.py
```

## Configuration & Environment

- ROI thresholds & fallback multipliers: [`config/roi_rules.yaml`](config/roi_rules.yaml)
- Land criteria & Mebane reference weights: [`config/land_criteria.yaml`](config/land_criteria.yaml)
- Environment variable names (zero secret values): [`.env.example`](.env.example)
- Operator skill runbook: [`../.agents/skills/build-b-auction-intel-v2/SKILL.md`](../.agents/skills/build-b-auction-intel-v2/SKILL.md)

## Public Sources Used (MASTER LAYER Compliant)

- NHTSA vPIC Vehicle API (US Federal Public Domain): `https://vpic.nhtsa.dot.gov/api/`
- NHTSA Recalls API (US Federal Public Domain): `https://api.nhtsa.gov/recalls/recallsByVehicle`
- NHTSA VIN Recall Lookup (Direct Reference URL): `https://www.nhtsa.gov/recalls`
