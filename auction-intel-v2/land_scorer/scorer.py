"""B3 — Fail-Closed NC Land Parcel Scorer engine and CLI.

Owner criteria (`config/land_criteria.yaml`):
- NC only: Caswell, Rockingham, Person counties
- Acreage: 1.0 to 5.0 acres (inclusive)
- Cash track: price < $30,000 (strictly less than)
- Auction track: price <= $5,000 (subset flagged distinctly)
- Fail-closed: missing/invalid price or acreage is EXCLUDED and counted — never estimated.
- Standing direct-URL rule: every emitted parcel carries a validated direct URL, or
  literal "URL not captured" (never a search-results URL).
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

try:
    from .adapters import fetch_public_feed_html, load_parcels_from_file, parse_county_tax_auction_html
except ImportError:  # pragma: no cover - direct script execution fallback
    from adapters import fetch_public_feed_html, load_parcels_from_file, parse_county_tax_auction_html

DEFAULT_CRITERIA_PATH = Path(__file__).resolve().parent.parent / "config" / "land_criteria.yaml"
LEGAL_ENTITY = "Tosson Services LLC dba Tosson Environmental Analytics"
URL_NOT_CAPTURED = "URL not captured"

SEARCH_PATH_MARKERS = (
    "/search",
    "/search-results",
    "/search_results",
    "/searchresults",
    "/results",
    "/find",
    "/browse",
)
SEARCH_QUERY_KEYS = frozenset(
    {"q", "query", "search", "keyword", "keywords", "search_query", "s", "term", "filter"}
)


def load_land_criteria(path: Path | str = DEFAULT_CRITERIA_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _parse_strict_positive_number(raw: Any) -> float | None:
    """Fail-closed numeric parser: returns float > 0 or None (never estimates/imputes)."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        if math.isnan(val) or math.isinf(val) or val <= 0.0:
            return None
        return val
    text = str(raw).strip()
    if not text or text.lower() in {"na", "n/a", "none", "null", "tbd", "unknown", "call", "-"}:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    cleaned = re.sub(r"\s*(acres?|ac\.?)$", "", cleaned, flags=re.IGNORECASE).strip()
    try:
        val = float(cleaned)
    except ValueError:
        return None
    if math.isnan(val) or math.isinf(val) or val <= 0.0:
        return None
    return val


def _parse_optional_coord(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        val = float(text)
        return None if (math.isnan(val) or math.isinf(val)) else val
    except ValueError:
        return None


def _normalize_county(raw: Any) -> str:
    text = str(raw or "").strip()
    text = re.sub(r"\s+county$", "", text, flags=re.IGNORECASE).strip()
    return text


def _normalize_state(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    if text in {"NC", "NORTH CAROLINA", "N.C."}:
        return "NC"
    return text


def sanitize_direct_url(raw_url: Any) -> tuple[str, str]:
    """Enforce owner's standing direct-URL rule.

    Returns `(emitted_url, status)` where:
    - Direct listing/parcel URL -> `(url, "DIRECT_URL_VALIDATED")`
    - Missing, malformed, homepage-only, or search-results URL -> `("URL not captured", "URL_NOT_CAPTURED")`
    """
    if raw_url is None:
        return URL_NOT_CAPTURED, "URL_NOT_CAPTURED"
    url = str(raw_url).strip()
    if not url:
        return URL_NOT_CAPTURED, "URL_NOT_CAPTURED"

    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return URL_NOT_CAPTURED, "URL_NOT_CAPTURED"

    path_lower = (parsed.path or "").lower().rstrip("/")
    # Reject bare domain roots without a listing/parcel path or query ID
    if not path_lower and not parsed.query:
        return URL_NOT_CAPTURED, "URL_NOT_CAPTURED"

    for marker in SEARCH_PATH_MARKERS:
        if marker in path_lower:
            return URL_NOT_CAPTURED, "URL_NOT_CAPTURED"

    query_params = parse_qs(parsed.query, keep_blank_values=True)
    lower_keys = {k.lower() for k in query_params.keys()}
    if lower_keys & SEARCH_QUERY_KEYS:
        return URL_NOT_CAPTURED, "URL_NOT_CAPTURED"

    return url, "DIRECT_URL_VALIDATED"


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in statute miles."""
    radius_miles = 3958.7613
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    return round(2.0 * radius_miles * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)


def _score_acreage(acreage: float, criteria: dict[str, Any]) -> float:
    b = criteria["scoring_benchmarks"]
    ideal_min = float(b["ideal_min_acres"])
    ideal_max = float(b["ideal_max_acres"])
    min_a = float(criteria["acreage"]["min_acres"])
    max_a = float(criteria["acreage"]["max_acres"])
    if ideal_min <= acreage <= ideal_max:
        return 1.0
    if acreage < ideal_min:
        span = max(ideal_min - min_a, 0.01)
        return max(0.5, 0.5 + 0.5 * ((acreage - min_a) / span))
    span = max(max_a - ideal_max, 0.01)
    return max(0.5, 0.5 + 0.5 * ((max_a - acreage) / span))


def _score_price_per_acre(price_per_acre: float, criteria: dict[str, Any]) -> float:
    b = criteria["scoring_benchmarks"]
    low = float(b["target_low_price_per_acre"])
    high = float(b["target_high_price_per_acre"])
    if price_per_acre <= low:
        return 1.0
    if price_per_acre >= high:
        return 0.1
    return round(1.0 - 0.9 * ((price_per_acre - low) / (high - low)), 4)


def _score_road_frontage(signal: Any) -> float:
    text = str(signal or "").strip().lower()
    if not text or text in {"unknown", "n/a", "none"}:
        return 0.25
    if any(k in text for k in ("landlocked", "no road", "no access", "none")):
        return 0.0
    if any(k in text for k in ("paved", "state road", "highway", "sr ", "nc-", "public road", "yes")):
        return 1.0
    if any(k in text for k in ("gravel", "easement", "private road", "deeded")):
        return 0.65
    return 0.4


def _score_zoning(signal: Any) -> float:
    text = str(signal or "").strip().lower()
    if not text or text in {"unknown", "n/a", "none"}:
        return 0.35
    if any(k in text for k in ("unzoned", "ra", "r-a", "ar", "agricultural", "rural", "residential-ag", "r-40", "r-20")):
        return 1.0
    if any(k in text for k in ("residential", "single family", "mixed")):
        return 0.8
    if any(k in text for k in ("floodway", "wetland", "conservation", "industrial only", "unbuildable")):
        return 0.1
    return 0.5


def score_parcels(
    raw_parcels: list[dict[str, Any]],
    *,
    criteria_path: Path | str = DEFAULT_CRITERIA_PATH,
) -> dict[str, Any]:
    """Filter fail-closed and score qualifying NC land parcels."""
    criteria = load_land_criteria(criteria_path)
    allowed_state = str(criteria["state"]).upper()
    allowed_counties = {c.lower(): c for c in criteria["counties"]}
    min_acres = float(criteria["acreage"]["min_acres"])
    max_acres = float(criteria["acreage"]["max_acres"])
    cash_max = float(criteria["pricing"]["cash_track_max_price"])
    auction_max = float(criteria["pricing"]["auction_track_max_price"])
    ref_lat = float(criteria["reference_point"]["lat"])
    ref_lon = float(criteria["reference_point"]["lon"])
    max_dist = float(criteria["reference_point"]["max_scored_distance_miles"])
    weights = criteria["scoring_weights"]

    excluded_counts: Counter[str] = Counter()
    excluded_records: list[dict[str, Any]] = []
    passing_parcels: list[dict[str, Any]] = []

    for idx, rec in enumerate(raw_parcels):
        parcel_id = str(rec.get("parcel_id") or rec.get("id") or f"ROW-{idx + 1}").strip()
        title = str(rec.get("title") or rec.get("address") or parcel_id).strip()

        price = _parse_strict_positive_number(rec.get("price"))
        if price is None:
            reason = "MISSING_OR_INVALID_PRICE"
            excluded_counts[reason] += 1
            excluded_records.append({"parcel_id": parcel_id, "title": title, "reason": reason})
            continue

        acreage = _parse_strict_positive_number(rec.get("acreage"))
        if acreage is None:
            reason = "MISSING_OR_INVALID_ACREAGE"
            excluded_counts[reason] += 1
            excluded_records.append({"parcel_id": parcel_id, "title": title, "reason": reason})
            continue

        state = _normalize_state(rec.get("state") or allowed_state)
        if state != allowed_state:
            reason = "OUTSIDE_STATE"
            excluded_counts[reason] += 1
            excluded_records.append({"parcel_id": parcel_id, "title": title, "reason": reason, "state": state})
            continue

        county_raw = _normalize_county(rec.get("county"))
        county_canonical = allowed_counties.get(county_raw.lower())
        if county_canonical is None:
            reason = "OUTSIDE_TARGET_COUNTIES"
            excluded_counts[reason] += 1
            excluded_records.append(
                {"parcel_id": parcel_id, "title": title, "reason": reason, "county": county_raw}
            )
            continue

        if acreage < min_acres or acreage > max_acres:
            reason = "OUTSIDE_ACREAGE_BOUNDS"
            excluded_counts[reason] += 1
            excluded_records.append(
                {"parcel_id": parcel_id, "title": title, "reason": reason, "acreage": acreage}
            )
            continue

        if price >= cash_max:
            reason = "ABOVE_CASH_TRACK_MAX_PRICE"
            excluded_counts[reason] += 1
            excluded_records.append(
                {"parcel_id": parcel_id, "title": title, "reason": reason, "price": price}
            )
            continue

        tracks = ["CASH_TRACK"]
        primary_track = "CASH_TRACK"
        if price <= auction_max:
            tracks.insert(0, "AUCTION_TRACK")
            primary_track = "AUCTION_TRACK"

        price_per_acre = round(price / acreage, 2)
        emitted_url, url_status = sanitize_direct_url(rec.get("url"))

        lat = _parse_optional_coord(rec.get("lat"))
        lon = _parse_optional_coord(rec.get("lon"))
        if lat is not None and lon is not None:
            dist_miles: float | None = haversine_miles(ref_lat, ref_lon, lat, lon)
            dist_ratio = max(0.0, 1.0 - (dist_miles / max_dist))
            coord_note = "COORDINATES_PROVIDED"
        else:
            dist_miles = None
            dist_ratio = 0.0
            coord_note = "COORDINATES_MISSING_NOT_IMPUTED"

        acre_pts = round(_score_acreage(acreage, criteria) * float(weights["acreage_fit"]), 2)
        ppa_pts = round(_score_price_per_acre(price_per_acre, criteria) * float(weights["price_per_acre"]), 2)
        road_pts = round(_score_road_frontage(rec.get("road_frontage")) * float(weights["road_frontage"]), 2)
        zoning_pts = round(_score_zoning(rec.get("zoning")) * float(weights["zoning_signal"]), 2)
        dist_pts = round(dist_ratio * float(weights["distance_from_mebane"]), 2)
        total_score = round(acre_pts + ppa_pts + road_pts + zoning_pts + dist_pts, 2)

        passing_parcels.append(
            {
                "parcel_id": parcel_id,
                "title": title,
                "county": county_canonical,
                "state": allowed_state,
                "acreage": round(acreage, 3),
                "price": round(price, 2),
                "price_per_acre": price_per_acre,
                "primary_track": primary_track,
                "tracks": tracks,
                "road_frontage": str(rec.get("road_frontage") or "Unknown").strip(),
                "zoning": str(rec.get("zoning") or "Unknown").strip(),
                "distance_from_mebane_miles": dist_miles,
                "coordinate_status": coord_note,
                "url": emitted_url,
                "url_status": url_status,
                "source": str(rec.get("source") or "input_feed").strip(),
                "score": total_score,
                "score_breakdown": {
                    "acreage_fit": acre_pts,
                    "price_per_acre": ppa_pts,
                    "road_frontage": road_pts,
                    "zoning_signal": zoning_pts,
                    "distance_from_mebane": dist_pts,
                },
            }
        )

    passing_parcels.sort(key=lambda p: (-p["score"], p["price_per_acre"], p["parcel_id"]))

    return {
        "module": "b3-land-parcel-scorer",
        "mode": "READ_ONLY_FAIL_CLOSED",
        "legal_entity": LEGAL_ENTITY,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "criteria": {
            "state": allowed_state,
            "counties": list(criteria["counties"]),
            "min_acres": min_acres,
            "max_acres": max_acres,
            "cash_track_max_price_exclusive": cash_max,
            "auction_track_max_price_inclusive": auction_max,
            "reference_point": criteria["reference_point"]["name"],
        },
        "counts": {
            "total_evaluated": len(raw_parcels),
            "passing": len(passing_parcels),
            "auction_track_passing": sum(1 for p in passing_parcels if p["primary_track"] == "AUCTION_TRACK"),
            "cash_track_only_passing": sum(1 for p in passing_parcels if p["primary_track"] == "CASH_TRACK"),
            "excluded": len(excluded_records),
        },
        "excluded_summary": dict(sorted(excluded_counts.items())),
        "excluded_records": excluded_records,
        "passing_parcels": passing_parcels,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    c = report["counts"]
    crit = report["criteria"]
    lines: list[str] = [
        "# B3 — NC Land Parcel Scorer Report (Fail-Closed)",
        "",
        f"- **Entity:** {report['legal_entity']}",
        f"- **Execution Mode:** `{report['mode']}` (read-only analysis; zero estimates/imputation for missing price or acreage)",
        f"- **Target Counties ({crit['state']}):** `{', '.join(crit['counties'])}`",
        f"- **Acreage Bounds:** `{crit['min_acres']} – {crit['max_acres']} acres`",
        f"- **Tracks:** `CASH_TRACK` (`< ${crit['cash_track_max_price_exclusive']:,.0f}`), `AUCTION_TRACK` (`<= ${crit['auction_track_max_price_inclusive']:,.0f}`)",
        f"- **Reference Point:** `{crit['reference_point']}`",
        f"- **Generated (UTC):** `{report['generated_at']}`",
        "",
        "## Evaluation Summary",
        "",
        "| Total Evaluated | Passing | Auction Track (<= $5k) | Cash Track Only (< $30k) | Excluded (Fail-Closed) |",
        "|---:|---:|---:|---:|---:|",
        f"| {c['total_evaluated']} | {c['passing']} | {c['auction_track_passing']} | {c['cash_track_only_passing']} | {c['excluded']} |",
        "",
        "## Ranked Passing Parcels (Direct URL Standing Rule Enforced)",
        "",
    ]

    if report["passing_parcels"]:
        lines.extend(
            [
                "| Rank | Parcel ID | County | Track | Acres | Price | $/Acre | Dist Mebane (mi) | Score | Direct URL |",
                "|---:|---|---|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for idx, p in enumerate(report["passing_parcels"], start=1):
            dist_s = f"{p['distance_from_mebane_miles']:.1f}" if p["distance_from_mebane_miles"] is not None else "n/a"
            url_cell = p["url"] if p["url"] == URL_NOT_CAPTURED else f"[Direct Listing]({p['url']})"
            lines.append(
                f"| {idx} | `{p['parcel_id']}` | {p['county']} | `{p['primary_track']}` | "
                f"{p['acreage']:.2f} | ${p['price']:,.2f} | ${p['price_per_acre']:,.2f} | "
                f"{dist_s} | **{p['score']:.2f}** | {url_cell} |"
            )
    else:
        lines.append("_No parcels met all owner criteria._")

    lines.extend(["", "## Fail-Closed Excluded Summary", ""])
    if report["excluded_summary"]:
        lines.extend(["| Exclusion Reason | Count |", "|---|---:|"])
        for reason, count in report["excluded_summary"].items():
            lines.append(f"| `{reason}` | {count} |")
    else:
        lines.append("_Zero parcels excluded._")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B3 Read-only Fail-Closed NC Land Parcel Scorer")
    parser.add_argument("--input", default=None, help="Local JSON, CSV, or HTML parcel feed file")
    parser.add_argument("--feed-url", default=None, help="Optional public county GIS / tax-auction HTML URL (read-only GET)")
    parser.add_argument("--default-county", default="", help="Default county name when parsing single-county HTML feed")
    parser.add_argument("--criteria", default=str(DEFAULT_CRITERIA_PATH), help="Path to land_criteria.yaml")
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-md", default=None)

    args = parser.parse_args(argv)
    if not args.input and not args.feed_url:
        parser.error("Provide --input <file> or --feed-url <url>")

    parcels: list[dict[str, Any]] = []
    if args.input:
        parcels.extend(load_parcels_from_file(args.input, default_county=args.default_county))
    if args.feed_url:
        html_text = fetch_public_feed_html(args.feed_url)
        parcels.extend(
            parse_county_tax_auction_html(
                html_text,
                base_url=args.feed_url,
                default_county=args.default_county,
                source_name=args.feed_url,
            )
        )

    report = score_parcels(parcels, criteria_path=args.criteria)
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
