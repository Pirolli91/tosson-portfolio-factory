"""Offline tests for B2 — HiBid Churn Tracker (title similarity + Pillow dHash)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AUCTION_DIR = WORKSPACE_ROOT / "auction-intel-v2"
if str(AUCTION_DIR) not in sys.path:
    sys.path.insert(0, str(AUCTION_DIR))

from hibid_churn.churn_tracker import (
    compute_title_similarity,
    main as churn_main,
    normalize_title,
    render_markdown_report,
    track_churn,
)
from hibid_churn.dhash import compute_dhash, hamming_distance

SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_b"
IMG_DIR = SYNTH_DIR / "hibid_images"


def test_pillow_dhash_near_identical_vs_distinct_images() -> None:
    h_prev = compute_dhash(IMG_DIR / "miter_saw_prev.png")
    h_curr = compute_dhash(IMG_DIR / "miter_saw_curr.png")
    h_cab = compute_dhash(IMG_DIR / "cabinet_dropped.png")
    h_comp = compute_dhash(IMG_DIR / "compressor_new.png")

    assert len(h_prev) == 16  # 64-bit hex
    assert hamming_distance(h_prev, h_curr) <= 10
    assert hamming_distance(h_prev, h_cab) > 15
    assert hamming_distance(h_cab, h_comp) > 15


def test_planted_relist_caught_with_title_and_pillow_dhash() -> None:
    report = track_churn(
        SYNTH_DIR / "hibid_prev.json",
        SYNTH_DIR / "hibid_curr.json",
        categories=["Tools"],
    )
    counts = report["counts"]
    assert counts["prev_lots_evaluated"] == 6  # Collectibles lot HB-1099 filtered out
    assert counts["curr_lots_evaluated"] == 6
    assert counts["UNCHANGED"] == 1
    assert counts["PRICE_UP"] == 1
    assert counts["PRICE_DOWN"] == 1
    assert counts["RELISTED"] == 2
    assert counts["NEW"] == 1
    assert counts["DROPPED"] == 1

    relisted_by_id = {item["lot_id"]: item for item in report["relisted"]}
    assert "HB-2004" in relisted_by_id
    saw_relist = relisted_by_id["HB-2004"]
    assert saw_relist["prior_lot_id"] == "HB-1004"
    assert saw_relist["match_method"] == "TITLE_AND_IMAGE"
    assert saw_relist["title_similarity"] >= 0.85
    assert saw_relist["dhash_hamming_distance"] is not None
    assert saw_relist["dhash_hamming_distance"] <= 10
    assert saw_relist["price_delta"] == -25.0

    # Second relist had no images => graceful text-only fallback
    ladder_relist = relisted_by_id["HB-2005"]
    assert ladder_relist["prior_lot_id"] == "HB-1005"
    assert ladder_relist["match_method"] == "TITLE_ONLY"
    assert ladder_relist["dhash_hamming_distance"] is None

    # Price movements accurate
    assert report["price_up"][0]["lot_id"] == "HB-1002"
    assert report["price_up"][0]["price_delta"] == 75.0
    assert report["price_down"][0]["lot_id"] == "HB-1003"
    assert report["price_down"][0]["price_delta"] == -30.0

    # Distinct new & dropped lots not falsely matched
    assert report["new"][0]["lot_id"] == "HB-2007"
    assert report["dropped"][0]["lot_id"] == "HB-1006"

    md = render_markdown_report(report)
    assert "TITLE_AND_IMAGE" in md
    assert "HB-2004" in md


def test_image_only_relist_detection_and_csv_field_map(tmp_path: Path) -> None:
    """Catches a re-listed lot whose title was completely rewritten, via Pillow dHash alone."""
    prev_csv = tmp_path / "prev.csv"
    curr_csv = tmp_path / "curr.csv"
    fmap = tmp_path / "fmap.yaml"

    prev_csv.write_text(
        "LotNumber,LeadTitle,CategoryName,HighBidAmount,LotDetailUrl,LocalThumbnailPath\n"
        "A1,Yellow Woodshop Saw,Tools,150,https://hibid.com/lot/A1,miter_saw_prev.png\n",
        encoding="utf-8",
    )
    curr_csv.write_text(
        "LotNumber,LeadTitle,CategoryName,HighBidAmount,LotDetailUrl,LocalThumbnailPath\n"
        "B9,Estate Garage Item Unlabelled,Tools,125,https://hibid.com/lot/B9,miter_saw_curr.png\n",
        encoding="utf-8",
    )
    fmap.write_text(
        "lot_id: LotNumber\n"
        "title: LeadTitle\n"
        "category: CategoryName\n"
        "current_bid: HighBidAmount\n"
        "url: LotDetailUrl\n"
        "image_path: LocalThumbnailPath\n",
        encoding="utf-8",
    )

    out_json = tmp_path / "churn.json"
    out_md = tmp_path / "churn.md"
    rc = churn_main(
        [
            "--prev",
            str(prev_csv),
            "--curr",
            str(curr_csv),
            "--image-dir",
            str(IMG_DIR),
            "--field-map",
            str(fmap),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    assert rc == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["counts"]["RELISTED"] == 1
    assert data["relisted"][0]["match_method"] == "IMAGE_ONLY"
    assert data["relisted"][0]["dhash_hamming_distance"] <= 10
    assert normalize_title("Lot #42: Test Item!") == "test item"
    assert compute_title_similarity("Lot #1: DeWalt Drill", "Lot #9: DeWalt Drill") == 1.0
