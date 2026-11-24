"""B2 — HiBid Churn Tracker engine and CLI.

Compares two chronological HiBid refresh snapshots (`--prev`, `--curr`) to detect:
- NEW lots
- RELISTED lots (via normalized title similarity + Pillow 64-bit dHash)
- PRICE_UP / PRICE_DOWN / UNCHANGED lots
- DROPPED lots

Strictly read-only analysis. Never places bids or alters live dashboard state.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from .dhash import compute_dhash, hamming_distance
except ImportError:  # pragma: no cover - direct script execution fallback
    from dhash import compute_dhash, hamming_distance

LEGAL_ENTITY = "Tosson Services LLC dba Tosson Environmental Analytics"

DEFAULT_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "lot_id": ("lot_id", "lotId", "id", "lot_number", "lotNumber", "lot_num"),
    "title": ("title", "lot_title", "lotTitle", "lead", "name", "description"),
    "category": ("category", "cat", "category_name", "categoryName", "group"),
    "current_bid": ("current_bid", "currentBid", "high_bid", "highBid", "price", "bid"),
    "url": ("url", "lot_url", "lotUrl", "link", "href"),
    "image_path": ("image_path", "imagePath", "local_image", "image", "img_path"),
    "snapshot_ts": ("snapshot_ts", "snapshotTs", "captured_at", "timestamp", "ts"),
}


@dataclass(frozen=True)
class SnapshotLot:
    lot_id: str
    title: str
    category: str
    current_bid: float
    url: str
    image_path: str | None
    snapshot_ts: str | None


def _parse_float(raw: Any, default: float = 0.0) -> float:
    if raw is None or raw == "":
        return default
    if isinstance(raw, (int, float)):
        return float(raw)
    cleaned = str(raw).strip().replace("$", "").replace(",", "")
    if not cleaned:
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def normalize_title(title: str) -> str:
    """Normalize lot titles by removing leading lot numbers, punctuation, and extra spaces."""
    text = title.lower().strip()
    text = re.sub(r"^\s*lot\s*#?\s*\d+\s*[:\-–—]?\s*", "", text)
    text = re.sub(r"\b(relist|re-listed|relisted|new arrival)\b", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_title_similarity(title_a: str, title_b: str) -> float:
    """Combined normalized token Jaccard + SequenceMatcher ratio in [0.0, 1.0]."""
    norm_a = normalize_title(title_a)
    norm_b = normalize_title(title_b)
    if not norm_a or not norm_b:
        return 0.0
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    union = tokens_a | tokens_b
    jaccard = len(tokens_a & tokens_b) / len(union) if union else 0.0
    seq_ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    return round(0.5 * jaccard + 0.5 * seq_ratio, 4)


def load_field_map(path: Path | str | None) -> dict[str, str]:
    if path is None:
        return {}
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Field map must be a mapping: {p}")
    return {str(k): str(v) for k, v in raw.items()}


def _extract_field(record: dict[str, Any], canonical: str, field_map: dict[str, str]) -> Any:
    if canonical in field_map and field_map[canonical] in record:
        return record[field_map[canonical]]
    for alias in DEFAULT_FIELD_ALIASES[canonical]:
        if alias in record and record[alias] not in (None, ""):
            return record[alias]
    # Case-insensitive fallback
    lowered = {str(k).strip().lower(): v for k, v in record.items()}
    for alias in DEFAULT_FIELD_ALIASES[canonical]:
        val = lowered.get(alias.lower())
        if val not in (None, ""):
            return val
    return None


def load_snapshot(
    snapshot_path: Path | str,
    *,
    field_map: dict[str, str] | None = None,
) -> tuple[str | None, list[SnapshotLot]]:
    """Load a HiBid refresh snapshot from JSON or CSV."""
    path = Path(snapshot_path)
    fmap = field_map or {}
    snapshot_ts: str | None = None
    raw_records: list[dict[str, Any]] = []

    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            snapshot_ts = payload.get("snapshot_ts") or payload.get("captured_at")
            raw_records = list(payload.get("lots") or payload.get("items") or [])
        elif isinstance(payload, list):
            raw_records = list(payload)
        else:
            raise ValueError(f"Unsupported JSON snapshot root in {path}")
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            raw_records = list(csv.DictReader(fh))
    else:
        raise ValueError(f"Unsupported snapshot file format (expected .json or .csv): {path}")

    lots: list[SnapshotLot] = []
    for rec in raw_records:
        lot_id = _extract_field(rec, "lot_id", fmap)
        title = _extract_field(rec, "title", fmap)
        if lot_id is None or title is None:
            continue
        rec_ts = _extract_field(rec, "snapshot_ts", fmap) or snapshot_ts
        if snapshot_ts is None and rec_ts:
            snapshot_ts = str(rec_ts)
        img_val = _extract_field(rec, "image_path", fmap)
        lots.append(
            SnapshotLot(
                lot_id=str(lot_id).strip(),
                title=str(title).strip(),
                category=str(_extract_field(rec, "category", fmap) or "Uncategorized").strip(),
                current_bid=round(_parse_float(_extract_field(rec, "current_bid", fmap), 0.0), 2),
                url=str(_extract_field(rec, "url", fmap) or "").strip(),
                image_path=str(img_val).strip() if img_val else None,
                snapshot_ts=str(rec_ts).strip() if rec_ts else None,
            )
        )
    return snapshot_ts, lots


def _resolve_image_path(
    raw_img: str | None,
    *,
    snapshot_dir: Path,
    image_dir: Path | None,
) -> Path | None:
    if not raw_img:
        return None
    candidate = Path(raw_img)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    if image_dir is not None:
        in_img_dir = image_dir / raw_img
        if in_img_dir.exists():
            return in_img_dir
    rel_snap = snapshot_dir / raw_img
    if rel_snap.exists():
        return rel_snap
    if candidate.exists():
        return candidate
    return None


def _safe_dhash(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return compute_dhash(path)
    except Exception:
        return None


def track_churn(
    prev_path: Path | str,
    curr_path: Path | str,
    *,
    categories: list[str] | None = None,
    image_dir: Path | str | None = None,
    field_map_path: Path | str | None = None,
    title_threshold: float = 0.72,
    max_hamming_distance: int = 10,
) -> dict[str, Any]:
    """Compare previous and current HiBid snapshots and classify every lot."""
    prev_p = Path(prev_path)
    curr_p = Path(curr_path)
    img_dir_p = Path(image_dir) if image_dir else None
    fmap = load_field_map(field_map_path)

    prev_ts, prev_lots_all = load_snapshot(prev_p, field_map=fmap)
    curr_ts, curr_lots_all = load_snapshot(curr_p, field_map=fmap)

    cat_filter = {c.strip().lower() for c in (categories or []) if c.strip()}
    if cat_filter:
        prev_lots = [l for l in prev_lots_all if l.category.lower() in cat_filter]
        curr_lots = [l for l in curr_lots_all if l.category.lower() in cat_filter]
    else:
        prev_lots = prev_lots_all
        curr_lots = curr_lots_all

    prev_by_id = {lot.lot_id: lot for lot in prev_lots}
    curr_by_id = {lot.lot_id: lot for lot in curr_lots}

    price_up: list[dict[str, Any]] = []
    price_down: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []

    for lot_id, c_lot in curr_by_id.items():
        if lot_id in prev_by_id:
            p_lot = prev_by_id[lot_id]
            delta = round(c_lot.current_bid - p_lot.current_bid, 2)
            delta_pct = round((delta / p_lot.current_bid) * 100.0, 2) if p_lot.current_bid > 0 else None
            entry = {
                "lot_id": c_lot.lot_id,
                "title": c_lot.title,
                "category": c_lot.category,
                "url": c_lot.url,
                "prior_bid": p_lot.current_bid,
                "current_bid": c_lot.current_bid,
                "price_delta": delta,
                "price_delta_pct": delta_pct,
            }
            if delta > 0:
                entry["classification"] = "PRICE_UP"
                price_up.append(entry)
            elif delta < 0:
                entry["classification"] = "PRICE_DOWN"
                price_down.append(entry)
            else:
                entry["classification"] = "UNCHANGED"
                unchanged.append(entry)

    prev_only = [lot for lid, lot in prev_by_id.items() if lid not in curr_by_id]
    curr_only = [lot for lid, lot in curr_by_id.items() if lid not in prev_by_id]

    prev_hashes: dict[str, str | None] = {
        lot.lot_id: _safe_dhash(_resolve_image_path(lot.image_path, snapshot_dir=prev_p.parent, image_dir=img_dir_p))
        for lot in prev_only
    }
    curr_hashes: dict[str, str | None] = {
        lot.lot_id: _safe_dhash(_resolve_image_path(lot.image_path, snapshot_dir=curr_p.parent, image_dir=img_dir_p))
        for lot in curr_only
    }

    # Build candidate re-list pairs scored deterministically
    candidate_pairs: list[tuple[float, str, float, int | None, SnapshotLot, SnapshotLot]] = []
    for c_lot in curr_only:
        c_hash = curr_hashes[c_lot.lot_id]
        for p_lot in prev_only:
            title_sim = compute_title_similarity(p_lot.title, c_lot.title)
            p_hash = prev_hashes[p_lot.lot_id]
            hdist = hamming_distance(p_hash, c_hash) if (p_hash and c_hash) else None

            title_match = title_sim >= title_threshold
            image_match = hdist is not None and hdist <= max_hamming_distance

            match_method: str | None = None
            if title_match and image_match:
                match_method = "TITLE_AND_IMAGE"
                combined_score = 2.0 + title_sim + (1.0 - (hdist / 64.0))
            elif image_match:
                match_method = "IMAGE_ONLY"
                combined_score = 1.5 + (1.0 - (hdist / 64.0)) + 0.25 * title_sim
            elif title_match and (hdist is None or hdist <= max_hamming_distance * 2):
                match_method = "TITLE_ONLY"
                combined_score = 1.0 + title_sim

            if match_method is not None:
                candidate_pairs.append((combined_score, match_method, title_sim, hdist, p_lot, c_lot))

    # Greedy 1-to-1 matching by highest combined confidence
    candidate_pairs.sort(key=lambda item: (-item[0], item[4].lot_id, item[5].lot_id))
    matched_prev_ids: set[str] = set()
    matched_curr_ids: set[str] = set()
    relisted: list[dict[str, Any]] = []

    for _, match_method, title_sim, hdist, p_lot, c_lot in candidate_pairs:
        if p_lot.lot_id in matched_prev_ids or c_lot.lot_id in matched_curr_ids:
            continue
        matched_prev_ids.add(p_lot.lot_id)
        matched_curr_ids.add(c_lot.lot_id)
        delta = round(c_lot.current_bid - p_lot.current_bid, 2)
        relisted.append(
            {
                "classification": "RELISTED",
                "lot_id": c_lot.lot_id,
                "title": c_lot.title,
                "category": c_lot.category,
                "url": c_lot.url,
                "prior_lot_id": p_lot.lot_id,
                "prior_title": p_lot.title,
                "prior_bid": p_lot.current_bid,
                "current_bid": c_lot.current_bid,
                "price_delta": delta,
                "title_similarity": title_sim,
                "dhash_hamming_distance": hdist,
                "prior_dhash": prev_hashes[p_lot.lot_id],
                "current_dhash": curr_hashes[c_lot.lot_id],
                "match_method": match_method,
            }
        )

    new_lots: list[dict[str, Any]] = [
        {
            "classification": "NEW",
            "lot_id": lot.lot_id,
            "title": lot.title,
            "category": lot.category,
            "url": lot.url,
            "current_bid": lot.current_bid,
        }
        for lot in curr_only
        if lot.lot_id not in matched_curr_ids
    ]

    dropped_lots: list[dict[str, Any]] = [
        {
            "classification": "DROPPED",
            "lot_id": lot.lot_id,
            "title": lot.title,
            "category": lot.category,
            "url": lot.url,
            "prior_bid": lot.current_bid,
        }
        for lot in prev_only
        if lot.lot_id not in matched_prev_ids
    ]

    return {
        "module": "b2-hibid-churn-tracker",
        "mode": "READ_ONLY_ANALYSIS",
        "legal_entity": LEGAL_ENTITY,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prev_snapshot": prev_p.name,
        "curr_snapshot": curr_p.name,
        "prev_snapshot_ts": prev_ts,
        "curr_snapshot_ts": curr_ts,
        "watched_categories": sorted(cat_filter) if cat_filter else ["ALL"],
        "parameters": {
            "title_similarity_threshold": title_threshold,
            "dhash_max_hamming_distance": max_hamming_distance,
        },
        "counts": {
            "prev_lots_evaluated": len(prev_lots),
            "curr_lots_evaluated": len(curr_lots),
            "NEW": len(new_lots),
            "RELISTED": len(relisted),
            "PRICE_UP": len(price_up),
            "PRICE_DOWN": len(price_down),
            "UNCHANGED": len(unchanged),
            "DROPPED": len(dropped_lots),
        },
        "relisted": relisted,
        "price_up": price_up,
        "price_down": price_down,
        "new": new_lots,
        "unchanged": unchanged,
        "dropped": dropped_lots,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    c = report["counts"]
    lines: list[str] = [
        "# B2 — HiBid Churn & Re-List Detection Report",
        "",
        f"- **Entity:** {report['legal_entity']}",
        f"- **Execution Mode:** `{report['mode']}` (no bids, no account changes)",
        f"- **Previous Snapshot:** `{report['prev_snapshot']}` (`{report['prev_snapshot_ts'] or 'n/a'}`)",
        f"- **Current Snapshot:** `{report['curr_snapshot']}` (`{report['curr_snapshot_ts'] or 'n/a'}`)",
        f"- **Watched Categories:** `{', '.join(report['watched_categories'])}`",
        f"- **Thresholds:** title similarity >= `{report['parameters']['title_similarity_threshold']}`, Pillow dHash Hamming <= `{report['parameters']['dhash_max_hamming_distance']}` bits",
        f"- **Generated (UTC):** `{report['generated_at']}`",
        "",
        "## Cycle Classification Summary",
        "",
        "| NEW | RELISTED | PRICE_UP | PRICE_DOWN | UNCHANGED | DROPPED |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {c['NEW']} | {c['RELISTED']} | {c['PRICE_UP']} | {c['PRICE_DOWN']} | {c['UNCHANGED']} | {c['DROPPED']} |",
        "",
        "## Detected Re-Listed Lots",
        "",
    ]

    if report["relisted"]:
        lines.extend(
            [
                "| Current Lot | Prior Lot | Title | Match Method | Title Sim | dHash Hamming | Prior Bid | Curr Bid | Delta |",
                "|---|---|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for item in report["relisted"]:
            h_str = str(item["dhash_hamming_distance"]) if item["dhash_hamming_distance"] is not None else "n/a"
            lines.append(
                f"| `{item['lot_id']}` | `{item['prior_lot_id']}` | {item['title']} | "
                f"`{item['match_method']}` | {item['title_similarity']:.4f} | {h_str} | "
                f"${item['prior_bid']:,.2f} | ${item['current_bid']:,.2f} | ${item['price_delta']:+,.2f} |"
            )
    else:
        lines.append("_No re-listed lots detected in this refresh cycle._")

    lines.extend(["", "## Price Movements (PRICE_UP / PRICE_DOWN)", ""])
    movers = report["price_up"] + report["price_down"]
    if movers:
        lines.extend(
            [
                "| Classification | Lot ID | Category | Title | Prior Bid | Curr Bid | Delta |",
                "|---|---|---|---|---:|---:|---:|",
            ]
        )
        for m in movers:
            lines.append(
                f"| `{m['classification']}` | `{m['lot_id']}` | {m['category']} | {m['title']} | "
                f"${m['prior_bid']:,.2f} | ${m['current_bid']:,.2f} | ${m['price_delta']:+,.2f} |"
            )
    else:
        lines.append("_No price movements detected._")

    lines.extend(["", "## New Lots", ""])
    if report["new"]:
        for n in report["new"]:
            lines.append(f"- `{n['lot_id']}` [{n['category']}] {n['title']} — `${n['current_bid']:,.2f}`")
    else:
        lines.append("_None._")

    lines.extend(["", "## Dropped Lots (Not Re-Listed)", ""])
    if report["dropped"]:
        for d in report["dropped"]:
            lines.append(f"- `{d['lot_id']}` [{d['category']}] {d['title']} — prior `${d['prior_bid']:,.2f}`")
    else:
        lines.append("_None._")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2 Read-only HiBid Churn Tracker")
    parser.add_argument("--prev", required=True, help="Previous snapshot JSON or CSV")
    parser.add_argument("--curr", required=True, help="Current snapshot JSON or CSV")
    parser.add_argument("--categories", default=None, help="Comma-separated watched categories filter")
    parser.add_argument("--image-dir", default=None, help="Optional directory containing cached lot images")
    parser.add_argument("--field-map", default=None, help="Optional YAML/JSON field mapping file")
    parser.add_argument("--title-threshold", type=float, default=0.72)
    parser.add_argument("--max-hamming", type=int, default=10)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-md", default=None)

    args = parser.parse_args(argv)
    cats = [c.strip() for c in args.categories.split(",")] if args.categories else None
    report = track_churn(
        args.prev,
        args.curr,
        categories=cats,
        image_dir=args.image_dir,
        field_map_path=args.field_map,
        title_threshold=args.title_threshold,
        max_hamming_distance=args.max_hamming,
    )
    md_text = render_markdown_report(report)
    if args.out_json:
        p = Path(args.out_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.out_md:
        p = Path(args.out_md)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md_text, encoding="utf-8")
    if not args.out_json and not args.out_md:
        print(md_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
