"""CSV format adapters for Liquidation.com and B-Stock liquidation manifests.

Read-only parsing only. Handles currency formatting (`$`, `,`), header aliases,
condition normalization, and grouping rows into lots.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

TWO_PLACES = Decimal("0.01")

LIQUIDATION_COM_HEADERS = {
    "item description",
    "unit retail",
    "ext. retail",
    "ext retail",
    "liquidation lot",
    "lot #",
}

BSTOCK_HEADERS = {
    "item title",
    "unit msrp",
    "ext msrp",
    "extended msrp",
    "b-stock lot",
    "auction id",
    "upc/ean",
    "retail price",
}


@dataclass(frozen=True)
class ManifestItem:
    lot_id: str
    sku_or_upc: str
    description: str
    qty: int
    unit_retail: Decimal
    ext_retail: Decimal
    condition_raw: str
    condition_tier: str


@dataclass
class ManifestLot:
    lot_id: str
    marketplace: str
    items: list[ManifestItem] = field(default_factory=list)
    lot_bid_price: Decimal | None = None
    buyers_premium_rate: Decimal | None = None
    shipping_estimate: Decimal | None = None
    handling_or_tax: Decimal | None = None


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def parse_currency(raw: str | int | float | Decimal | None) -> Decimal | None:
    """Parse currency/number strings like '$1,234.50' or '400' into Decimal."""
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    cleaned = str(raw).strip()
    if not cleaned or cleaned.lower() in {"na", "n/a", "none", "null", "-"}:
        return None
    cleaned = cleaned.replace("$", "").replace(",", "").replace("%", "").strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_rate(raw: str | int | float | Decimal | None) -> Decimal | None:
    """Parse rate either as decimal (0.10) or percent (10 or 10%)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    has_pct = "%" in text
    val = parse_currency(text)
    if val is None:
        return None
    if has_pct or val > Decimal("1"):
        return val / Decimal("100")
    return val


def parse_int(raw: str | int | float | None, default: int = 1) -> int:
    if raw is None:
        return default
    cleaned = str(raw).strip().replace(",", "")
    if not cleaned:
        return default
    try:
        val = int(Decimal(cleaned))
        return val if val > 0 else default
    except (InvalidOperation, ValueError):
        return default


def normalize_condition(raw: str | None) -> str:
    """Normalize marketplace condition strings to roi_rules.yaml tier keys."""
    if not raw:
        return "unknown"
    text = re.sub(r"[^a-z0-9]+", " ", raw.strip().lower()).strip()
    if not text:
        return "unknown"
    if any(tok in text for tok in ("salvage", "damaged", "defective", "scrap", "parts", "uninspected")):
        return "salvage"
    if any(tok in text for tok in ("customer return", "return", "used", "pre owned", "scratch", "dent")):
        return "customer_return"
    if any(tok in text for tok in ("open box", "like new", "refurb", "reconditioned")):
        return "open_box"
    if any(tok in text for tok in ("shelf pull", "overstock", "closeout", "excess")):
        return "shelf_pull"
    if "new" in text:
        return "new"
    return "unknown"


def _norm_header(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower().lstrip("\ufeff"))


def detect_format(headers: Iterable[str]) -> str:
    """Auto-detect `liquidation_com` vs `bstock` from CSV column headers."""
    norm = {_norm_header(h) for h in headers if h}
    bstock_score = sum(1 for h in BSTOCK_HEADERS if h in norm)
    liq_score = sum(1 for h in LIQUIDATION_COM_HEADERS if h in norm)
    if any("bstock" in h or "b-stock" in h or "msrp" in h for h in norm):
        bstock_score += 2
    if any("liquidation" in h or "unit retail" in h or "ext. retail" in h for h in norm):
        liq_score += 2
    if bstock_score > liq_score:
        return "bstock"
    return "liquidation_com"


def _first_present(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        val = row.get(key)
        if val is not None and str(val).strip() != "":
            return str(val).strip()
    return ""


def parse_manifest_csv(
    csv_path: Path | str,
    *,
    fmt: str = "auto",
    default_lot_id: str | None = None,
) -> tuple[str, list[ManifestLot]]:
    """Parse a Liquidation.com or B-Stock manifest CSV into grouped ManifestLot records."""
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"Manifest CSV has no headers: {path}")
        resolved_fmt = detect_format(reader.fieldnames) if fmt == "auto" else fmt.lower()
        if resolved_fmt not in {"liquidation_com", "bstock"}:
            raise ValueError(f"Unsupported manifest format: {fmt}")

        lots_by_id: dict[str, ManifestLot] = {}
        fallback_lot_id = default_lot_id or path.stem.upper()

        for raw_row in reader:
            row = {_norm_header(k): (v.strip() if isinstance(v, str) else "") for k, v in raw_row.items() if k}
            if not any(row.values()):
                continue

            lot_id = (
                _first_present(
                    row,
                    ("lot_id", "lot id", "lot #", "lot", "auction id", "auction_id", "b-stock lot", "liquidation lot"),
                )
                or fallback_lot_id
            )
            description = _first_present(
                row,
                ("description", "item description", "item title", "title", "product name", "item", "product"),
            )
            if not description:
                continue

            sku_or_upc = _first_present(row, ("upc", "upc/ean", "sku", "sku/upc", "asin", "item #", "part number"))
            qty = parse_int(_first_present(row, ("qty", "quantity", "units", "count")), default=1)
            unit_retail = parse_currency(
                _first_present(
                    row,
                    (
                        "unit retail",
                        "unit_retail",
                        "unit msrp",
                        "unit_msrp",
                        "msrp",
                        "retail price",
                        "unit price",
                        "orig. retail",
                    ),
                )
            )
            ext_retail = parse_currency(
                _first_present(
                    row,
                    ("ext. retail", "ext retail", "ext_retail", "ext msrp", "extended msrp", "total retail", "total msrp"),
                )
            )
            if unit_retail is None and ext_retail is not None:
                unit_retail = quantize_money(ext_retail / Decimal(qty))
            elif unit_retail is None:
                unit_retail = Decimal("0.00")
            if ext_retail is None:
                ext_retail = quantize_money(unit_retail * Decimal(qty))
            else:
                ext_retail = quantize_money(ext_retail)
            unit_retail = quantize_money(unit_retail)

            condition_raw = _first_present(row, ("condition", "item condition", "grade", "lot condition")) or "Unknown"
            condition_tier = normalize_condition(condition_raw)

            if lot_id not in lots_by_id:
                lots_by_id[lot_id] = ManifestLot(lot_id=lot_id, marketplace=resolved_fmt)
            lot = lots_by_id[lot_id]

            # Populate lot-level financial metadata if present in CSV columns
            bid_val = parse_currency(
                _first_present(
                    row,
                    (
                        "lot_bid_price",
                        "lot bid price",
                        "bid_price",
                        "bid price",
                        "current_bid",
                        "current bid",
                        "lot price",
                        "lot_price",
                    ),
                )
            )
            if bid_val is not None and lot.lot_bid_price is None:
                lot.lot_bid_price = quantize_money(bid_val)

            bp_rate = parse_rate(
                _first_present(
                    row,
                    (
                        "buyers_premium_rate",
                        "buyers premium rate",
                        "buyer's premium rate",
                        "buyers premium",
                        "bp_rate",
                    ),
                )
            )
            if bp_rate is not None and lot.buyers_premium_rate is None:
                lot.buyers_premium_rate = bp_rate

            ship_val = parse_currency(
                _first_present(
                    row,
                    (
                        "shipping_estimate",
                        "shipping estimate",
                        "shipping",
                        "freight",
                        "shipping cost",
                        "shipping_cost",
                    ),
                )
            )
            if ship_val is not None and lot.shipping_estimate is None:
                lot.shipping_estimate = quantize_money(ship_val)

            handling_val = parse_currency(
                _first_present(
                    row,
                    (
                        "handling_or_tax",
                        "handling or tax",
                        "handling",
                        "tax",
                        "fees_other",
                        "other_fees",
                    ),
                )
            )
            if handling_val is not None and lot.handling_or_tax is None:
                lot.handling_or_tax = quantize_money(handling_val)

            lot.items.append(
                ManifestItem(
                    lot_id=lot_id,
                    sku_or_upc=sku_or_upc,
                    description=description,
                    qty=qty,
                    unit_retail=unit_retail,
                    ext_retail=ext_retail,
                    condition_raw=condition_raw,
                    condition_tier=condition_tier,
                )
            )

    return resolved_fmt, list(lots_by_id.values())
