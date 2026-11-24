"""Offline tests for B1 — Manifest ROI Analyser (zero dependency on fixtures/)."""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AUCTION_DIR = WORKSPACE_ROOT / "auction-intel-v2"
if str(AUCTION_DIR) not in sys.path:
    sys.path.insert(0, str(AUCTION_DIR))

from manifest_roi.adapters import detect_format, parse_currency, parse_manifest_csv
from manifest_roi.analyser import analyse_manifest, main as roi_main, render_markdown_report

SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_b"


def test_format_auto_detection_and_currency_parsing() -> None:
    assert parse_currency("$1,250.50") == Decimal("1250.50")
    assert parse_currency("($45.00)") == Decimal("-45.00")
    assert parse_currency("N/A") is None

    fmt_liq, lots_liq = parse_manifest_csv(SYNTH_DIR / "liquidation_com_sample.csv", fmt="auto")
    assert fmt_liq == "liquidation_com"
    assert len(lots_liq) == 3

    fmt_bst, lots_bst = parse_manifest_csv(SYNTH_DIR / "bstock_sample.csv", fmt="auto")
    assert fmt_bst == "bstock"
    assert len(lots_bst) == 1
    assert detect_format(["Auction ID", "Item Title", "Unit MSRP"]) == "bstock"


def test_hand_check_liquidation_com_public_comp_fallback() -> None:
    """Reproduces exact penny-level hand calculation on sample Liquidation.com lots."""
    report = analyse_manifest(SYNTH_DIR / "liquidation_com_sample.csv")
    assert report["active_comp_mode"] == "PUBLIC_COMP_FALLBACK"
    assert report["sold_history_loaded"] is False
    assert report["verdict_counts"] == {"STRONG": 1, "MARGINAL": 1, "PASS": 1}

    by_id = {lot["lot_id"]: lot for lot in report["lots"]}

    # Lot LIQ-2026-101 hand-check:
    # 4*$200*0.45=$360 + 5*$160*0.55=$440 + 2*$100*0.40=$80 => gross_mid=$880.00
    # bid=$400 + 10% BP ($40) + $60 shipping + $0 handling => landed_cost=$500.00
    # selling_fees = 10% of $880 = $88.00 => net_resale_mid=$792.00
    # net_profit = $792.00 - $500.00 = $292.00 => roi_pct = 58.40% => STRONG
    lot1 = by_id["LIQ-2026-101"]
    assert lot1["total_ext_retail"] == 1800.00
    assert lot1["lot_bid_price"] == 400.00
    assert lot1["buyers_premium"] == 40.00
    assert lot1["shipping_estimate"] == 60.00
    assert lot1["handling_or_tax"] == 0.00
    assert lot1["landed_cost"] == 500.00
    assert lot1["gross_resale_low"] == 748.00
    assert lot1["gross_resale_mid"] == 880.00
    assert lot1["gross_resale_high"] == 1012.00
    assert lot1["selling_fees"] == 88.00
    assert lot1["net_resale_mid"] == 792.00
    assert lot1["net_profit"] == 292.00
    assert lot1["roi_pct"] == 58.40
    assert lot1["verdict"] == "STRONG"

    # Lot LIQ-2026-102 => MARGINAL (24.62%, $64.00 profit)
    lot2 = by_id["LIQ-2026-102"]
    assert lot2["landed_cost"] == 260.00
    assert lot2["gross_resale_mid"] == 360.00
    assert lot2["selling_fees"] == 36.00
    assert lot2["net_resale_mid"] == 324.00
    assert lot2["net_profit"] == 64.00
    assert lot2["roi_pct"] == 24.62
    assert lot2["verdict"] == "MARGINAL"

    # Lot LIQ-2026-103 => PASS (-51.79%, -$72.50 profit)
    lot3 = by_id["LIQ-2026-103"]
    assert lot3["landed_cost"] == 140.00
    assert lot3["gross_resale_mid"] == 75.00
    assert lot3["net_resale_mid"] == 67.50
    assert lot3["net_profit"] == -72.50
    assert lot3["roi_pct"] == -51.79
    assert lot3["verdict"] == "PASS"

    md = render_markdown_report(report)
    assert "PUBLIC_COMP_FALLBACK" in md
    assert "LIQ-2026-101" in md
    assert "$292.00" in md


def test_bstock_zero_buyers_premium_and_hybrid_sold_history_mode() -> None:
    """B-Stock defaults to 0% buyer's premium and switches to HYBRID when partially matched."""
    report = analyse_manifest(
        SYNTH_DIR / "bstock_sample.csv",
        sold_history_path=SYNTH_DIR / "sold_history_sample.csv",
    )
    assert report["marketplace_format"] == "bstock"
    assert report["active_comp_mode"] == "HYBRID"
    assert report["sold_history_loaded"] is True

    lot = report["lots"][0]
    assert lot["lot_id"] == "BST-88401"
    assert lot["buyers_premium_rate"] == 0.0
    assert lot["buyers_premium"] == 0.0
    assert lot["landed_cost"] == 400.00  # $350 bid + $0 BP + $50 freight
    assert lot["matched_sold_history_items"] == 1
    assert lot["fallback_comp_items"] == 1
    # 6 * median(115, 125)=$120 => $720 (sold history) + 4 * ($120*0.40)=$192 (fallback) = $912.00
    assert lot["gross_resale_mid"] == 912.00
    assert lot["selling_fees"] == 91.20
    assert lot["net_resale_mid"] == 820.80
    assert lot["net_profit"] == 420.80
    assert lot["roi_pct"] == 105.20
    assert lot["verdict"] == "STRONG"


def test_owner_sold_history_full_match_and_cli_output(tmp_path: Path) -> None:
    # Single-lot manifest whose items are all in sold_history_sample.csv
    mini_manifest = tmp_path / "mini_liq.csv"
    mini_manifest.write_text(
        "Lot #,Item Description,Qty,Unit Retail,Condition,Lot Bid Price,Shipping Estimate\n"
        "LOT-FULL,DeWalt 20V MAX Brushless Drill Kit,2,$200.00,Shelf-Pull,$100.00,$20.00\n"
        "LOT-FULL,Klein Tools Digital Multimeter,2,$100.00,Open-Box,$100.00,$20.00\n",
        encoding="utf-8",
    )
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    rc = roi_main(
        [
            "--manifest",
            str(mini_manifest),
            "--sold-history",
            str(SYNTH_DIR / "sold_history_sample.csv"),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    assert rc == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["active_comp_mode"] == "OWNER_SOLD_HISTORY"
    assert "OWNER_SOLD_HISTORY" in out_md.read_text(encoding="utf-8")
