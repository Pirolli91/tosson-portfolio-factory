"""B3 — Read-only Fail-Closed NC Land Parcel Scorer."""
from __future__ import annotations

from .adapters import (
    fetch_public_feed_html,
    load_parcels_from_csv,
    load_parcels_from_file,
    load_parcels_from_json,
    parse_county_tax_auction_html,
)
from .scorer import (
    URL_NOT_CAPTURED,
    haversine_miles,
    load_land_criteria,
    render_markdown_report,
    sanitize_direct_url,
    score_parcels,
)

__all__ = [
    "URL_NOT_CAPTURED",
    "fetch_public_feed_html",
    "haversine_miles",
    "load_land_criteria",
    "load_parcels_from_csv",
    "load_parcels_from_file",
    "load_parcels_from_json",
    "parse_county_tax_auction_html",
    "render_markdown_report",
    "sanitize_direct_url",
    "score_parcels",
]
