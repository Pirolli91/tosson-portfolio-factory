# B4 — Kia Carnival (2022+) Checker Report (Isolated Monitor Mode)

- **Entity:** Tosson Services LLC dba Tosson Environmental Analytics
- **Execution Mode:** `MONITOR_ONLY` (strictly separate from general auction modules B1–B3; no buying, bidding, or dealer inquiries)
- **Listings Evaluated:** `5`
- **VIP Lounge Flagged Out:** `1`
- **SC266 Open VINs Flagged:** `1`
- **Generated (UTC):** `2026-11-24T00:20:29Z`

## Evaluated Listings

| Listing ID | Year / Model | VIN | Trim Filter | SC266 Recall Status | Overall Verdict | NHTSA VIN Recall Link |
|---|---|---|---|---|---|---|
| `CARN-001` | 2024 KIA Carnival | `KNDNC5H39R6300001` | `PASS` | `SC266_COMPLETED` | **PASS_MONITOR_CANDIDATE** | [Check VIN on NHTSA](https://www.nhtsa.gov/recalls?vin=KNDNC5H39R6300001) |
| `CARN-002` | 2023 KIA Carnival | `KNDNE5H35P6200002` | `FLAGGED_OUT_VIP_LOUNGE` | `SC266_COMPLETED` | **FLAGGED_OUT_VIP_LOUNGE** | [Check VIN on NHTSA](https://www.nhtsa.gov/recalls?vin=KNDNE5H35P6200002) |
| `CARN-003` | 2023 KIA Carnival | `KNDNE5H31P6200003` | `PASS` | `SC266_OPEN` | **FLAG_RECALL_SC266_OPEN** | [Check VIN on NHTSA](https://www.nhtsa.gov/recalls?vin=KNDNE5H31P6200003) |
| `CARN-004` | 2022 KIA Carnival | `KNDNC5H37N6100004` | `PASS` | `SC266_MODEL_YEAR_APPLICABLE_VERIFY_VIN` | **REVIEW_VERIFY_SC266_OR_TRIM** | [Check VIN on NHTSA](https://www.nhtsa.gov/recalls?vin=KNDNC5H37N6100004) |
| `OTHER-005` | 2021 HONDA Odyssey | `5FNRL6H78MB000005` | `PASS` | `SC266_NOT_LISTED_FOR_MODEL_YEAR` | **REJECT_WRONG_VEHICLE** | [Check VIN on NHTSA](https://www.nhtsa.gov/recalls?vin=5FNRL6H78MB000005) |

### Listing Details

- **`CARN-001` (2024 Kia Carnival EX 8-Passenger Minivan)** — Verdict: `PASS_MONITOR_CANDIDATE` | Trim: `PASS` (Target EX / SX 8-passenger trim detected (no VIP Lounge indicators).) | SC266: `SC266_COMPLETED` (`https://www.nhtsa.gov/recalls?vin=KNDNC5H39R6300001`)
- **`CARN-002` (2023 Kia Carnival SX Prestige — VIP Lounge Seat Package)** — Verdict: `FLAGGED_OUT_VIP_LOUNGE` | Trim: `FLAGGED_OUT_VIP_LOUNGE` (VIP Lounge / SX Prestige 7-passenger second-row seats excluded per owner criteria.) | SC266: `SC266_COMPLETED` (`https://www.nhtsa.gov/recalls?vin=KNDNE5H35P6200002`)
- **`CARN-003` (2023 Kia Carnival SX 8-Passenger)** — Verdict: `FLAG_RECALL_SC266_OPEN` | Trim: `PASS` (Target EX / SX 8-passenger trim detected (no VIP Lounge indicators).) | SC266: `SC266_OPEN` (`https://www.nhtsa.gov/recalls?vin=KNDNE5H31P6200003`)
- **`CARN-004` (2022 Kia Carnival EX)** — Verdict: `REVIEW_VERIFY_SC266_OR_TRIM` | Trim: `PASS` (Target EX / SX 8-passenger trim detected (no VIP Lounge indicators).) | SC266: `SC266_MODEL_YEAR_APPLICABLE_VERIFY_VIN` (`https://www.nhtsa.gov/recalls?vin=KNDNC5H37N6100004`)
- **`OTHER-005` (2021 Honda Odyssey EX-L)** — Verdict: `REJECT_WRONG_VEHICLE` | Trim: `PASS` (Target EX / SX 8-passenger trim detected (no VIP Lounge indicators).) | SC266: `SC266_NOT_LISTED_FOR_MODEL_YEAR` (`https://www.nhtsa.gov/recalls?vin=5FNRL6H78MB000005`)

## Summer-2027 KFA Finance-Clause Checklist Stub

> **NOTICE: DOCUMENT CHECKLIST GENERATOR ONLY — NOT LEGAL OR FINANCIAL ADVICE.**  
> This stub flags candidate keywords and produces a structured pre-signing review checklist.
> Confirm every contract term directly on the final signed paperwork or with a qualified professional.

- **Contract Text Scanned:** `YES`

| Clause ID | Status | Check Item | Document Section |
|---|---|---|---|
| `NO_MINIMUM_FINANCING_TERM` | `FAVORABLE_PHRASE_FOUND` | No Minimum Financing Term / Early-Payoff Hold Restriction | Retail Installment Sale Contract — Prepayment / Payment Terms & Any Dealer Addendum |
| `ZERO_PREPAYMENT_PENALTY` | `FAVORABLE_PHRASE_FOUND` | Zero Prepayment Penalty | Federal TILA Disclosure Box ('Prepayment') & Prepayment Paragraph |
| `SIMPLE_INTEREST_DAILY_ACCRUAL` | `FAVORABLE_PHRASE_FOUND` | Simple-Interest Daily Accrual (Not Precomputed) | How Finance Charge Is Figured / Simple Finance Charge Section |
| `DEALER_CHARGEBACK_VS_BORROWER_OBLIGATION` | `RISK_PHRASE_FOUND` | Dealer Rebate Chargeback vs. Borrower Contractual Obligation | Dealer Addenda, 'We Owe', Rebate Assignment & Side Agreements |

- **`NO_MINIMUM_FINANCING_TERM` (FAVORABLE_PHRASE_FOUND):** Confirm the Retail Installment Sale Contract (RISC) contains NO borrower covenant requiring the loan to remain open for a minimum number of months or payments (e.g., 90 days / 3–6 payments) before payoff.
  - *Favorable phrase match:* `...C TEST SAMPLE) 1. PREPAYMENT: You may prepay all or part of the unpaid principal balance at any time. Federal Truth-in-Lending Prepa...`
- **`ZERO_PREPAYMENT_PENALTY` (FAVORABLE_PHRASE_FOUND):** Confirm the Federal Truth-in-Lending (TILA) disclosure box marks 'will not' for prepayment penalty and the contract explicitly states $0 / no penalty for paying off early.
  - *Favorable phrase match:* `...Disclosure: If you pay early, you will not have to pay a penalty. 2. HOW WE FIGURE FINANCE CHARGE:...`
- **`SIMPLE_INTEREST_DAILY_ACCRUAL` (FAVORABLE_PHRASE_FOUND):** Confirm finance charges accrue on a daily simple-interest basis on unpaid principal so early payoff eliminates unearned future interest (not precomputed / Rule of 78s).
  - *Favorable phrase match:* `...RETAIL INSTALLMENT SALE CONTRACT — SIMPLE FINANCE CHARGE (SYNTHETIC TEST SAMPLE) 1. PREPAY...`
  - *Favorable phrase match:* `...GURE FINANCE CHARGE: We figure the Finance Charge on a daily basis at the Annual Percentage Rate o...`
- **`DEALER_CHARGEBACK_VS_BORROWER_OBLIGATION` (RISK_PHRASE_FOUND):** Verify that any KFA dealer-reserve/incentive chargeback remains strictly between KFA and the dealer — confirm NO borrower-signed addendum or side-agreement obligates the buyer to reimburse the dealer for lost rebate or reserve upon early payoff.
  - *Risk phrase match:* `...ADDENDUM (PLANTED TEST CLAUSE): Borrower agrees to repay the dealer rebate if the loan is paid off wit...`
