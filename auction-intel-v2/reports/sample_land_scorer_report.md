# B3 — NC Land Parcel Scorer Report (Fail-Closed)

- **Entity:** Tosson Services LLC dba Tosson Environmental Analytics
- **Execution Mode:** `READ_ONLY_FAIL_CLOSED` (read-only analysis; zero estimates/imputation for missing price or acreage)
- **Target Counties (NC):** `Caswell, Rockingham, Person`
- **Acreage Bounds:** `1.0 – 5.0 acres`
- **Tracks:** `CASH_TRACK` (`< $30,000`), `AUCTION_TRACK` (`<= $5,000`)
- **Reference Point:** `Mebane, NC`
- **Generated (UTC):** `2026-11-24T00:20:00Z`

## Evaluation Summary

| Total Evaluated | Passing | Auction Track (<= $5k) | Cash Track Only (< $30k) | Excluded (Fail-Closed) |
|---:|---:|---:|---:|---:|
| 11 | 4 | 1 | 3 | 7 |

## Ranked Passing Parcels (Direct URL Standing Rule Enforced)

| Rank | Parcel ID | County | Track | Acres | Price | $/Acre | Dist Mebane (mi) | Score | Direct URL |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | `CAS-00412` | Caswell | `AUCTION_TRACK` | 2.40 | $4,200.00 | $1,750.00 | 21.0 | **94.75** | [Direct Listing](https://caswellcountync.gov/tax-sales/parcels/CAS-00412) |
| 2 | `PER-01988` | Person | `CASH_TRACK` | 3.50 | $22,500.00 | $6,428.57 | 21.3 | **79.18** | [Direct Listing](https://personcountync.gov/gis/parcel/PER-01988) |
| 3 | `ROC-00771` | Rockingham | `CASH_TRACK` | 1.50 | $18,000.00 | $12,000.00 | 28.5 | **67.36** | URL not captured |
| 4 | `CAS-00805` | Caswell | `CASH_TRACK` | 2.00 | $25,000.00 | $12,500.00 | n/a | **48.40** | URL not captured |

## Fail-Closed Excluded Summary

| Exclusion Reason | Count |
|---|---:|
| `ABOVE_CASH_TRACK_MAX_PRICE` | 1 |
| `MISSING_OR_INVALID_ACREAGE` | 1 |
| `MISSING_OR_INVALID_PRICE` | 1 |
| `OUTSIDE_ACREAGE_BOUNDS` | 2 |
| `OUTSIDE_STATE` | 1 |
| `OUTSIDE_TARGET_COUNTIES` | 1 |
