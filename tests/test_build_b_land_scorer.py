"""Offline tests for B3 — Fail-Closed NC Land Parcel Scorer & Direct URL Enforcer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AUCTION_DIR = WORKSPACE_ROOT / "auction-intel-v2"
if str(AUCTION_DIR) not in sys.path:
    sys.path.insert(0, str(AUCTION_DIR))

from land_scorer.adapters import load_parcels_from_file, parse_county_tax_auction_html
from land_scorer.scorer import (
    URL_NOT_CAPTURED,
    haversine_miles,
    main as land_main,
    render_markdown_report,
    sanitize_direct_url,
    score_parcels,
)

SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_b"


def test_direct_url_standing_rule_rejects_search_links_and_empty() -> None:
    assert sanitize_direct_url("https://caswellcountync.gov/tax-sales/parcels/CAS-00412") == (
        "https://caswellcountync.gov/tax-sales/parcels/CAS-00412",
        "DIRECT_URL_VALIDATED",
    )
    for bad in (
        "",
        None,
        "https://example.gov/search?q=caswell",
        "https://example.gov/search_results/page2",
        "https://example.gov/listings?keyword=acreage",
        "https://example.gov/results?query=land",
        "https://example.gov/",
        "not-a-url",
    ):
        emitted, status = sanitize_direct_url(bad)
        assert emitted == URL_NOT_CAPTURED
        assert status == "URL_NOT_CAPTURED"


def test_fail_closed_filtering_tracks_and_direct_url_enforcement() -> None:
    raw = load_parcels_from_file(SYNTH_DIR / "land_parcels_sample.json")
    report = score_parcels(raw)

    assert report["counts"]["total_evaluated"] == 11
    assert report["counts"]["passing"] == 4
    assert report["counts"]["auction_track_passing"] == 1
    assert report["counts"]["cash_track_only_passing"] == 3
    assert report["counts"]["excluded"] == 7

    # Verify every exclusion reason counted fail-closed
    excluded = report["excluded_summary"]
    assert excluded == {
        "ABOVE_CASH_TRACK_MAX_PRICE": 1,
        "MISSING_OR_INVALID_ACREAGE": 1,
        "MISSING_OR_INVALID_PRICE": 1,
        "OUTSIDE_ACREAGE_BOUNDS": 2,
        "OUTSIDE_STATE": 1,
        "OUTSIDE_TARGET_COUNTIES": 1,
    }

    passing = report["passing_parcels"]
    allowed_counties = {"Caswell", "Rockingham", "Person"}
    for p in passing:
        assert p["state"] == "NC"
        assert p["county"] in allowed_counties
        assert 1.0 <= p["acreage"] <= 5.0
        assert 0.0 < p["price"] < 30000.0
        assert p["url"] == URL_NOT_CAPTURED or (
            p["url"].startswith("https://") and "/search" not in p["url"] and "?q=" not in p["url"]
        )

    by_id = {p["parcel_id"]: p for p in passing}
    # Top-ranked auction track parcel in Caswell
    assert passing[0]["parcel_id"] == "CAS-00412"
    assert by_id["CAS-00412"]["primary_track"] == "AUCTION_TRACK"
    assert by_id["CAS-00412"]["url"] == "https://caswellcountync.gov/tax-sales/parcels/CAS-00412"
    assert by_id["CAS-00412"]["distance_from_mebane_miles"] is not None

    # Search-URL parcel and blank-URL parcel MUST emit literal "URL not captured"
    assert by_id["ROC-00771"]["url"] == URL_NOT_CAPTURED
    assert by_id["ROC-00771"]["url_status"] == "URL_NOT_CAPTURED"
    assert by_id["CAS-00805"]["url"] == URL_NOT_CAPTURED
    assert by_id["CAS-00805"]["distance_from_mebane_miles"] is None
    assert by_id["CAS-00805"]["coordinate_status"] == "COORDINATES_MISSING_NOT_IMPUTED"

    # Mebane self-distance == 0
    assert haversine_miles(36.0960, -79.2670, 36.0960, -79.2670) == 0.0


def test_html_county_tax_auction_adapter_and_cli(tmp_path: Path) -> None:
    html_text = (SYNTH_DIR / "land_county_feed_sample.html").read_text(encoding="utf-8")
    parsed = parse_county_tax_auction_html(
        html_text,
        base_url="https://caswellcountync.gov/tax-sales/",
        default_county="Caswell",
    )
    assert len(parsed) == 3
    report = score_parcels(parsed)
    assert report["counts"]["passing"] == 2
    assert report["counts"]["excluded"] == 1
    assert report["excluded_summary"]["MISSING_OR_INVALID_PRICE"] == 1

    by_id = {p["parcel_id"]: p for p in report["passing_parcels"]}
    assert by_id["CAS-TAX-901"]["url"] == "https://caswellcountync.gov/parcels/CAS-TAX-901"
    assert by_id["CAS-TAX-901"]["primary_track"] == "AUCTION_TRACK"
    assert by_id["CAS-TAX-902"]["url"] == URL_NOT_CAPTURED  # search link stripped

    out_json = tmp_path / "land.json"
    out_md = tmp_path / "land.md"
    rc = land_main(
        [
            "--input",
            str(SYNTH_DIR / "land_parcels_sample.json"),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    assert rc == 0
    assert json.loads(out_json.read_text(encoding="utf-8"))["counts"]["passing"] == 4
    md = render_markdown_report(report)
    assert URL_NOT_CAPTURED in md
