# B2 — HiBid Churn & Re-List Detection Report

- **Entity:** Tosson Services LLC dba Tosson Environmental Analytics
- **Execution Mode:** `READ_ONLY_ANALYSIS` (no bids, no account changes)
- **Previous Snapshot:** `hibid_prev.json` (`2026-11-20T12:00:00Z`)
- **Current Snapshot:** `hibid_curr.json` (`2026-11-23T12:00:00Z`)
- **Watched Categories:** `tools`
- **Thresholds:** title similarity >= `0.72`, Pillow dHash Hamming <= `10` bits
- **Generated (UTC):** `2026-11-24T00:20:00Z`

## Cycle Classification Summary

| NEW | RELISTED | PRICE_UP | PRICE_DOWN | UNCHANGED | DROPPED |
|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 1 | 1 | 1 | 1 |

## Detected Re-Listed Lots

| Current Lot | Prior Lot | Title | Match Method | Title Sim | dHash Hamming | Prior Bid | Curr Bid | Delta |
|---|---|---|---|---:|---:|---:|---:|---:|
| `HB-2004` | `HB-1004` | Lot #2004 - DeWalt 10-Inch Sliding Compound Miter Saw DWS779 | `TITLE_AND_IMAGE` | 1.0000 | 3 | $210.00 | $185.00 | $-25.00 |
| `HB-2005` | `HB-1005` | Lot #2005 - Werner 8 Foot Fiberglass Step Ladder 300 lb Capacity | `TITLE_ONLY` | 0.8971 | n/a | $55.00 | $50.00 | $-5.00 |

## Price Movements (PRICE_UP / PRICE_DOWN)

| Classification | Lot ID | Category | Title | Prior Bid | Curr Bid | Delta |
|---|---|---|---|---:|---:|---:|
| `PRICE_UP` | `HB-1002` | Tools | Lot #1002: Honda EU2200i Inverter Generator | $450.00 | $525.00 | $+75.00 |
| `PRICE_DOWN` | `HB-1003` | Tools | Lot #1003: Stihl MS 250 Chainsaw 18 Inch Bar | $180.00 | $150.00 | $-30.00 |

## New Lots

- `HB-2007` [Tools] Lot #2007: Bostitch 6 Gallon Pancake Air Compressor — `$65.00`

## Dropped Lots (Not Re-Listed)

- `HB-1006` [Tools] Lot #1006: Craftsman 5-Drawer Rolling Tool Cabinet — prior `$135.00`
