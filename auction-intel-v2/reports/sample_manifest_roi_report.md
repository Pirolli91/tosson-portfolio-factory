# B1 — Manifest ROI Analysis Report

- **Entity:** Tosson Services LLC dba Tosson Environmental Analytics
- **Execution Mode:** `READ_ONLY_ANALYSIS` (no bids, no purchases, no marketplace mutations)
- **Active Resale-Comp Mode:** **`PUBLIC_COMP_FALLBACK`**
- **Marketplace Format:** `liquidation_com`
- **Manifest File:** `liquidation_com_sample.csv`
- **Sold-History Records Loaded:** `0`
- **Generated (UTC):** `2026-11-24T00:20:29Z`

## Summary by Verdict

| STRONG | MARGINAL | PASS | Total Lots |
|---:|---:|---:|---:|
| 1 | 1 | 1 | 3 |

## Per-Lot Arithmetic Breakdown

### Lot `LIQ-2026-101` — Verdict: **STRONG** (`PUBLIC_COMP_FALLBACK`)

| Metric | Amount / Value | Formula / Basis |
|---|---:|---|
| Total Extended MSRP / Retail | $1,800.00 | 3 line items (11 units) |
| Lot Bid Price | $400.00 | Manifest / CLI bid input |
| Buyer's Premium (10.0%) | $40.00 | `lot_bid_price * 0.10` |
| Shipping Estimate | $60.00 | Manifest / CLI shipping estimate |
| Handling or Tax | $0.00 | Manifest / CLI handling/tax |
| **Landed Cost** | **$500.00** | `bid + premium + shipping + handling/tax` |
| Gross Resale Range (Low / Mid / High) | $748.00 / **$880.00** / $1,012.00 | `PUBLIC_COMP_FALLBACK` (0 history / 3 fallback) |
| Selling Fees (10.0%) | $88.00 | `gross_resale_mid * 0.10` |
| **Net Resale (Mid)** | **$792.00** | `gross_resale_mid - selling_fees` |
| **Net Profit (Mid)** | **$292.00** | `net_resale_mid - landed_cost` |
| **ROI %** | **58.40%** | `(net_profit / landed_cost) * 100` |
| **Verdict** | **STRONG** | STRONG: ROI >= 40% & profit >= $150; MARGINAL: ROI >= 15% & profit > $0; else PASS |

#### Line Items

| SKU/UPC | Description | Qty | Condition | Unit Retail | Comp Source | Unit Mid | Gross Mid |
|---|---|---:|---|---:|---|---:|---:|
| 885911550011 | DeWalt 20V MAX Brushless Drill Kit | 4 | Shelf-Pull (`shelf_pull`) | $200.00 | `PUBLIC_COMP_FALLBACK` (0.45x) | $90.00 | $360.00 |
| 045242500022 | Milwaukee M18 Compact Impact Driver | 5 | New (`new`) | $160.00 | `PUBLIC_COMP_FALLBACK` (0.55x) | $88.00 | $440.00 |
| 092644690033 | Klein Tools Digital Multimeter | 2 | Open-Box (`open_box`) | $100.00 | `PUBLIC_COMP_FALLBACK` (0.40x) | $40.00 | $80.00 |

### Lot `LIQ-2026-102` — Verdict: **MARGINAL** (`PUBLIC_COMP_FALLBACK`)

| Metric | Amount / Value | Formula / Basis |
|---|---:|---|
| Total Extended MSRP / Retail | $1,000.00 | 2 line items (8 units) |
| Lot Bid Price | $200.00 | Manifest / CLI bid input |
| Buyer's Premium (10.0%) | $20.00 | `lot_bid_price * 0.10` |
| Shipping Estimate | $40.00 | Manifest / CLI shipping estimate |
| Handling or Tax | $0.00 | Manifest / CLI handling/tax |
| **Landed Cost** | **$260.00** | `bid + premium + shipping + handling/tax` |
| Gross Resale Range (Low / Mid / High) | $306.00 / **$360.00** / $414.00 | `PUBLIC_COMP_FALLBACK` (0 history / 2 fallback) |
| Selling Fees (10.0%) | $36.00 | `gross_resale_mid * 0.10` |
| **Net Resale (Mid)** | **$324.00** | `gross_resale_mid - selling_fees` |
| **Net Profit (Mid)** | **$64.00** | `net_resale_mid - landed_cost` |
| **ROI %** | **24.62%** | `(net_profit / landed_cost) * 100` |
| **Verdict** | **MARGINAL** | STRONG: ROI >= 40% & profit >= $150; MARGINAL: ROI >= 15% & profit > $0; else PASS |

#### Line Items

| SKU/UPC | Description | Qty | Condition | Unit Retail | Comp Source | Unit Mid | Gross Mid |
|---|---|---:|---|---:|---|---:|---:|
| 088381810044 | Makita 18V Circular Saw Bare Tool | 4 | Open-Box (`open_box`) | $150.00 | `PUBLIC_COMP_FALLBACK` (0.40x) | $60.00 | $240.00 |
| 000346480055 | Bosch Laser Distance Measure | 4 | Customer-Return (`customer_return`) | $100.00 | `PUBLIC_COMP_FALLBACK` (0.30x) | $30.00 | $120.00 |

### Lot `LIQ-2026-103` — Verdict: **PASS** (`PUBLIC_COMP_FALLBACK`)

| Metric | Amount / Value | Formula / Basis |
|---|---:|---|
| Total Extended MSRP / Retail | $500.00 | 1 line items (10 units) |
| Lot Bid Price | $100.00 | Manifest / CLI bid input |
| Buyer's Premium (10.0%) | $10.00 | `lot_bid_price * 0.10` |
| Shipping Estimate | $30.00 | Manifest / CLI shipping estimate |
| Handling or Tax | $0.00 | Manifest / CLI handling/tax |
| **Landed Cost** | **$140.00** | `bid + premium + shipping + handling/tax` |
| Gross Resale Range (Low / Mid / High) | $63.80 / **$75.00** / $86.30 | `PUBLIC_COMP_FALLBACK` (0 history / 1 fallback) |
| Selling Fees (10.0%) | $7.50 | `gross_resale_mid * 0.10` |
| **Net Resale (Mid)** | **$67.50** | `gross_resale_mid - selling_fees` |
| **Net Profit (Mid)** | **$-72.50** | `net_resale_mid - landed_cost` |
| **ROI %** | **-51.79%** | `(net_profit / landed_cost) * 100` |
| **Verdict** | **PASS** | STRONG: ROI >= 40% & profit >= $150; MARGINAL: ROI >= 15% & profit > $0; else PASS |

#### Line Items

| SKU/UPC | Description | Qty | Condition | Unit Retail | Comp Source | Unit Mid | Gross Mid |
|---|---|---:|---|---:|---|---:|---:|
| 700123450066 | Assorted Small Kitchen Appliances | 10 | Salvage (`salvage`) | $50.00 | `PUBLIC_COMP_FALLBACK` (0.15x) | $7.50 | $75.00 |

