"""B1 — Manifest ROI Analyser engine and CLI.

Computes explicit per-lot landed cost, resale comp range (OWNER_SOLD_HISTORY,
HYBRID, or PUBLIC_COMP_FALLBACK), selling fees, net profit, ROI %, and verdict
band (STRONG / MARGINAL / PASS). Strictly read-only analysis.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

try:
    from .adapters import ManifestLot, parse_currency, parse_manifest_csv, quantize_money
except ImportError:  # pragma: no cover - direct script execution fallback
    from adapters import ManifestLot, parse_currency, parse_manifest_csv, quantize_money

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "roi_rules.yaml"
LEGAL_ENTITY = "Tosson Services LLC dba Tosson Environmental Analytics"

STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "pack",
        "set",
        "kit",
        "new",
        "used",
        "lot",
        "box",
        "qty",
        "pcs",
        "piece",
    }
)


@dataclass(frozen=True)
class SoldComp:
    item: str
    cost: Decimal | None
    sold_price: Decimal
    tokens: frozenset[str]


def _tokenize(text: str) -> frozenset[str]:
    raw_tokens = re.findall(r"[a-z0-9]+", text.lower())
    filtered = {tok for tok in raw_tokens if len(tok) > 1 and tok not in STOPWORDS}
    return frozenset(filtered or raw_tokens)


def load_roi_rules(rules_path: Path | str = DEFAULT_RULES_PATH) -> dict[str, Any]:
    with Path(rules_path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_sold_history(csv_path: Path | str | None) -> list[SoldComp]:
    """Load owner sold-history CSV (`item,cost,sold_price` with flexible aliases)."""
    if csv_path is None:
        return []
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Sold history CSV not found: {path}")
    comps: list[SoldComp] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw_row in reader:
            row = {k.strip().lower().lstrip("\ufeff"): (v.strip() if isinstance(v, str) else "") for k, v in raw_row.items() if k}
            item = row.get("item") or row.get("title") or row.get("description") or row.get("product") or ""
            sold_val = parse_currency(
                row.get("sold_price") or row.get("sold price") or row.get("sold") or row.get("sale_price")
            )
            cost_val = parse_currency(row.get("cost") or row.get("buy_cost") or row.get("purchase_price"))
            if not item or sold_val is None or sold_val <= Decimal("0"):
                continue
            comps.append(
                SoldComp(
                    item=item,
                    cost=quantize_money(cost_val) if cost_val is not None else None,
                    sold_price=quantize_money(sold_val),
                    tokens=_tokenize(item),
                )
            )
    return comps


def _match_sold_comps(description: str, sold_history: list[SoldComp], min_overlap: float) -> list[SoldComp]:
    if not sold_history:
        return []
    item_tokens = _tokenize(description)
    if not item_tokens:
        return []
    scored: list[tuple[float, SoldComp]] = []
    for comp in sold_history:
        if not comp.tokens:
            continue
        inter = len(item_tokens & comp.tokens)
        if inter == 0:
            continue
        # Symmetric Dice / overlap score rewards strong shared product identity
        overlap = (2.0 * inter) / (len(item_tokens) + len(comp.tokens))
        if overlap >= min_overlap:
            scored.append((overlap, comp))
    if not scored:
        return []
    best_score = max(s for s, _ in scored)
    return [c for s, c in scored if s >= best_score - 0.10]


def assign_verdict(roi_pct: Decimal, net_profit: Decimal, rules: dict[str, Any]) -> str:
    bands = rules["verdict_bands"]
    strong_min_roi = Decimal(str(bands["strong"]["min_roi_pct"]))
    strong_min_profit = Decimal(str(bands["strong"]["min_net_profit"]))
    marginal_min_roi = Decimal(str(bands["marginal"]["min_roi_pct"]))
    marginal_min_profit_excl = Decimal(str(bands["marginal"]["min_net_profit_exclusive"]))

    if roi_pct >= strong_min_roi and net_profit >= strong_min_profit:
        return "STRONG"
    if roi_pct >= marginal_min_roi and net_profit > marginal_min_profit_excl:
        return "MARGINAL"
    return "PASS"


def analyse_lot(
    lot: ManifestLot,
    *,
    rules: dict[str, Any],
    sold_history: list[SoldComp] | None = None,
    override_bid_price: Decimal | None = None,
    override_buyers_premium_rate: Decimal | None = None,
    override_shipping: Decimal | None = None,
    override_handling_or_tax: Decimal | None = None,
    override_selling_fee_rate: Decimal | None = None,
) -> dict[str, Any]:
    """Compute full line-item and lot-level ROI breakdown for a single ManifestLot."""
    history = sold_history or []
    mp_defaults = rules["marketplace_defaults"]
    default_bp_rate = Decimal(
        str(mp_defaults.get(lot.marketplace, mp_defaults["default"])["buyers_premium_rate"])
    )
    selling_fee_rate = (
        override_selling_fee_rate
        if override_selling_fee_rate is not None
        else Decimal(str(rules["selling_fees"]["marketplace_fee_rate"]))
    )
    spread = Decimal(str(rules["public_comp_fallback"]["range_spread_pct"]))
    cond_mults = rules["public_comp_fallback"]["condition_multipliers"]
    min_overlap = float(rules["sold_history_matching"]["min_token_overlap"])

    lot_bid_price = quantize_money(
        override_bid_price
        if override_bid_price is not None
        else (lot.lot_bid_price if lot.lot_bid_price is not None else Decimal("0.00"))
    )
    buyers_premium_rate = (
        override_buyers_premium_rate
        if override_buyers_premium_rate is not None
        else (lot.buyers_premium_rate if lot.buyers_premium_rate is not None else default_bp_rate)
    )
    shipping_estimate = quantize_money(
        override_shipping
        if override_shipping is not None
        else (lot.shipping_estimate if lot.shipping_estimate is not None else Decimal("0.00"))
    )
    handling_or_tax = quantize_money(
        override_handling_or_tax
        if override_handling_or_tax is not None
        else (lot.handling_or_tax if lot.handling_or_tax is not None else Decimal("0.00"))
    )

    buyers_premium = quantize_money(lot_bid_price * buyers_premium_rate)
    landed_cost = quantize_money(lot_bid_price + buyers_premium + shipping_estimate + handling_or_tax)

    gross_resale_low = Decimal("0.00")
    gross_resale_mid = Decimal("0.00")
    gross_resale_high = Decimal("0.00")
    total_ext_retail = Decimal("0.00")
    total_units = 0
    matched_items = 0
    fallback_items = 0
    item_breakdowns: list[dict[str, Any]] = []

    for item in lot.items:
        total_units += item.qty
        total_ext_retail += item.ext_retail
        matches = _match_sold_comps(item.description, history, min_overlap)
        if matches:
            matched_items += 1
            prices = [m.sold_price for m in matches]
            unit_mid = quantize_money(Decimal(str(statistics.median(prices))))
            if len(prices) >= 2:
                unit_low = quantize_money(min(prices))
                unit_high = quantize_money(max(prices))
            else:
                unit_low = quantize_money(unit_mid * (Decimal("1") - spread))
                unit_high = quantize_money(unit_mid * (Decimal("1") + spread))
            comp_source = "OWNER_SOLD_HISTORY"
            multiplier_used: float | None = None
            matched_titles = [m.item for m in matches]
        else:
            fallback_items += 1
            mult = Decimal(str(cond_mults.get(item.condition_tier, cond_mults["unknown"])))
            unit_mid = quantize_money(item.unit_retail * mult)
            unit_low = quantize_money(unit_mid * (Decimal("1") - spread))
            unit_high = quantize_money(unit_mid * (Decimal("1") + spread))
            comp_source = "PUBLIC_COMP_FALLBACK"
            multiplier_used = float(mult)
            matched_titles = []

        line_low = quantize_money(unit_low * Decimal(item.qty))
        line_mid = quantize_money(unit_mid * Decimal(item.qty))
        line_high = quantize_money(unit_high * Decimal(item.qty))

        gross_resale_low += line_low
        gross_resale_mid += line_mid
        gross_resale_high += line_high

        item_breakdowns.append(
            {
                "sku_or_upc": item.sku_or_upc,
                "description": item.description,
                "qty": item.qty,
                "condition_raw": item.condition_raw,
                "condition_tier": item.condition_tier,
                "unit_retail": float(item.unit_retail),
                "ext_retail": float(item.ext_retail),
                "comp_source": comp_source,
                "fallback_multiplier": multiplier_used,
                "matched_sold_comps": matched_titles,
                "unit_resale_low": float(unit_low),
                "unit_resale_mid": float(unit_mid),
                "unit_resale_high": float(unit_high),
                "gross_resale_low": float(line_low),
                "gross_resale_mid": float(line_mid),
                "gross_resale_high": float(line_high),
            }
        )

    gross_resale_low = quantize_money(gross_resale_low)
    gross_resale_mid = quantize_money(gross_resale_mid)
    gross_resale_high = quantize_money(gross_resale_high)
    total_ext_retail = quantize_money(total_ext_retail)

    selling_fees = quantize_money(gross_resale_mid * selling_fee_rate)
    net_resale_mid = quantize_money(gross_resale_mid - selling_fees)
    net_resale_low = quantize_money(gross_resale_low - quantize_money(gross_resale_low * selling_fee_rate))
    net_resale_high = quantize_money(gross_resale_high - quantize_money(gross_resale_high * selling_fee_rate))
    net_profit = quantize_money(net_resale_mid - landed_cost)
    if landed_cost > Decimal("0"):
        roi_pct = quantize_money((net_profit / landed_cost) * Decimal("100"))
    else:
        roi_pct = Decimal("0.00")

    verdict = assign_verdict(roi_pct, net_profit, rules)

    if matched_items > 0 and fallback_items == 0:
        lot_comp_mode = "OWNER_SOLD_HISTORY"
    elif matched_items > 0 and fallback_items > 0:
        lot_comp_mode = "HYBRID"
    else:
        lot_comp_mode = "PUBLIC_COMP_FALLBACK"

    return {
        "lot_id": lot.lot_id,
        "marketplace": lot.marketplace,
        "comp_mode": lot_comp_mode,
        "item_count": len(lot.items),
        "total_units": total_units,
        "matched_sold_history_items": matched_items,
        "fallback_comp_items": fallback_items,
        "total_ext_retail": float(total_ext_retail),
        "lot_bid_price": float(lot_bid_price),
        "buyers_premium_rate": float(buyers_premium_rate),
        "buyers_premium": float(buyers_premium),
        "shipping_estimate": float(shipping_estimate),
        "handling_or_tax": float(handling_or_tax),
        "landed_cost": float(landed_cost),
        "gross_resale_low": float(gross_resale_low),
        "gross_resale_mid": float(gross_resale_mid),
        "gross_resale_high": float(gross_resale_high),
        "selling_fee_rate": float(selling_fee_rate),
        "selling_fees": float(selling_fees),
        "net_resale_low": float(net_resale_low),
        "net_resale_mid": float(net_resale_mid),
        "net_resale_high": float(net_resale_high),
        "net_profit": float(net_profit),
        "roi_pct": float(roi_pct),
        "verdict": verdict,
        "items": item_breakdowns,
    }


def analyse_manifest(
    manifest_path: Path | str,
    *,
    fmt: str = "auto",
    rules_path: Path | str = DEFAULT_RULES_PATH,
    sold_history_path: Path | str | None = None,
    override_bid_price: Decimal | None = None,
    override_buyers_premium_rate: Decimal | None = None,
    override_shipping: Decimal | None = None,
    override_handling_or_tax: Decimal | None = None,
    override_selling_fee_rate: Decimal | None = None,
) -> dict[str, Any]:
    rules = load_roi_rules(rules_path)
    sold_history = load_sold_history(sold_history_path)
    resolved_fmt, lots = parse_manifest_csv(manifest_path, fmt=fmt)

    lot_results = [
        analyse_lot(
            lot,
            rules=rules,
            sold_history=sold_history,
            override_bid_price=override_bid_price,
            override_buyers_premium_rate=override_buyers_premium_rate,
            override_shipping=override_shipping,
            override_handling_or_tax=override_handling_or_tax,
            override_selling_fee_rate=override_selling_fee_rate,
        )
        for lot in lots
    ]

    modes = {lr["comp_mode"] for lr in lot_results}
    if not lot_results or modes == {"PUBLIC_COMP_FALLBACK"}:
        active_comp_mode = "PUBLIC_COMP_FALLBACK"
    elif modes == {"OWNER_SOLD_HISTORY"}:
        active_comp_mode = "OWNER_SOLD_HISTORY"
    else:
        active_comp_mode = "HYBRID"

    verdict_counts = {"STRONG": 0, "MARGINAL": 0, "PASS": 0}
    for lr in lot_results:
        verdict_counts[lr["verdict"]] = verdict_counts.get(lr["verdict"], 0) + 1

    return {
        "module": "b1-manifest-roi-analyser",
        "mode": "READ_ONLY_ANALYSIS",
        "legal_entity": LEGAL_ENTITY,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest_file": str(Path(manifest_path).name),
        "marketplace_format": resolved_fmt,
        "active_comp_mode": active_comp_mode,
        "sold_history_loaded": bool(sold_history),
        "sold_history_records": len(sold_history),
        "verdict_counts": verdict_counts,
        "lots": lot_results,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# B1 — Manifest ROI Analysis Report",
        "",
        f"- **Entity:** {report['legal_entity']}",
        f"- **Execution Mode:** `{report['mode']}` (no bids, no purchases, no marketplace mutations)",
        f"- **Active Resale-Comp Mode:** **`{report['active_comp_mode']}`**",
        f"- **Marketplace Format:** `{report['marketplace_format']}`",
        f"- **Manifest File:** `{report['manifest_file']}`",
        f"- **Sold-History Records Loaded:** `{report['sold_history_records']}`",
        f"- **Generated (UTC):** `{report['generated_at']}`",
        "",
        "## Summary by Verdict",
        "",
        "| STRONG | MARGINAL | PASS | Total Lots |",
        "|---:|---:|---:|---:|",
        f"| {report['verdict_counts'].get('STRONG', 0)} | {report['verdict_counts'].get('MARGINAL', 0)} | {report['verdict_counts'].get('PASS', 0)} | {len(report['lots'])} |",
        "",
        "## Per-Lot Arithmetic Breakdown",
        "",
    ]

    for lot in report["lots"]:
        lines.extend(
            [
                f"### Lot `{lot['lot_id']}` — Verdict: **{lot['verdict']}** (`{lot['comp_mode']}`)",
                "",
                "| Metric | Amount / Value | Formula / Basis |",
                "|---|---:|---|",
                f"| Total Extended MSRP / Retail | ${lot['total_ext_retail']:,.2f} | {lot['item_count']} line items ({lot['total_units']} units) |",
                f"| Lot Bid Price | ${lot['lot_bid_price']:,.2f} | Manifest / CLI bid input |",
                f"| Buyer's Premium ({lot['buyers_premium_rate'] * 100:.1f}%) | ${lot['buyers_premium']:,.2f} | `lot_bid_price * {lot['buyers_premium_rate']:.2f}` |",
                f"| Shipping Estimate | ${lot['shipping_estimate']:,.2f} | Manifest / CLI shipping estimate |",
                f"| Handling or Tax | ${lot['handling_or_tax']:,.2f} | Manifest / CLI handling/tax |",
                f"| **Landed Cost** | **${lot['landed_cost']:,.2f}** | `bid + premium + shipping + handling/tax` |",
                f"| Gross Resale Range (Low / Mid / High) | ${lot['gross_resale_low']:,.2f} / **${lot['gross_resale_mid']:,.2f}** / ${lot['gross_resale_high']:,.2f} | `{lot['comp_mode']}` ({lot['matched_sold_history_items']} history / {lot['fallback_comp_items']} fallback) |",
                f"| Selling Fees ({lot['selling_fee_rate'] * 100:.1f}%) | ${lot['selling_fees']:,.2f} | `gross_resale_mid * {lot['selling_fee_rate']:.2f}` |",
                f"| **Net Resale (Mid)** | **${lot['net_resale_mid']:,.2f}** | `gross_resale_mid - selling_fees` |",
                f"| **Net Profit (Mid)** | **${lot['net_profit']:,.2f}** | `net_resale_mid - landed_cost` |",
                f"| **ROI %** | **{lot['roi_pct']:.2f}%** | `(net_profit / landed_cost) * 100` |",
                f"| **Verdict** | **{lot['verdict']}** | STRONG: ROI >= 40% & profit >= $150; MARGINAL: ROI >= 15% & profit > $0; else PASS |",
                "",
                "#### Line Items",
                "",
                "| SKU/UPC | Description | Qty | Condition | Unit Retail | Comp Source | Unit Mid | Gross Mid |",
                "|---|---|---:|---|---:|---|---:|---:|",
            ]
        )
        for item in lot["items"]:
            mult_note = (
                f" ({item['fallback_multiplier']:.2f}x)" if item["fallback_multiplier"] is not None else ""
            )
            lines.append(
                f"| {item['sku_or_upc'] or '-'} | {item['description']} | {item['qty']} | "
                f"{item['condition_raw']} (`{item['condition_tier']}`) | ${item['unit_retail']:,.2f} | "
                f"`{item['comp_source']}`{mult_note} | ${item['unit_resale_mid']:,.2f} | ${item['gross_resale_mid']:,.2f} |"
            )
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B1 Read-only Manifest ROI Analyser")
    parser.add_argument("--manifest", required=True, help="Path to Liquidation.com or B-Stock manifest CSV")
    parser.add_argument("--format", default="auto", choices=["auto", "liquidation_com", "bstock"])
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="Path to roi_rules.yaml")
    parser.add_argument("--sold-history", default=None, help="Optional path to owner sold-history CSV")
    parser.add_argument("--bid-price", default=None, help="Override lot bid price")
    parser.add_argument("--buyers-premium-rate", default=None, help="Override buyer's premium rate (e.g. 0.10)")
    parser.add_argument("--shipping", default=None, help="Override shipping estimate")
    parser.add_argument("--handling-tax", default=None, help="Override handling/tax estimate")
    parser.add_argument("--selling-fee-rate", default=None, help="Override marketplace selling fee rate")
    parser.add_argument("--out-json", default=None, help="Output path for JSON report")
    parser.add_argument("--out-md", default=None, help="Output path for Markdown report")

    args = parser.parse_args(argv)
    report = analyse_manifest(
        args.manifest,
        fmt=args.format,
        rules_path=args.rules,
        sold_history_path=args.sold_history,
        override_bid_price=parse_currency(args.bid_price),
        override_buyers_premium_rate=Decimal(args.buyers_premium_rate) if args.buyers_premium_rate is not None else None,
        override_shipping=parse_currency(args.shipping),
        override_handling_or_tax=parse_currency(args.handling_tax),
        override_selling_fee_rate=Decimal(args.selling_fee_rate) if args.selling_fee_rate is not None else None,
    )

    md_text = render_markdown_report(report)
    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(md_text + "\n", encoding="utf-8")
    if not args.out_json and not args.out_md:
        print(md_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
