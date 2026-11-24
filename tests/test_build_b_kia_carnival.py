"""Offline tests for B4 — STRICTLY SEPARATE Kia Carnival Checker (Monitor Mode Only)."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AUCTION_DIR = WORKSPACE_ROOT / "auction-intel-v2"
if str(AUCTION_DIR) not in sys.path:
    sys.path.insert(0, str(AUCTION_DIR))

from kia_carnival.checker import check_listings, classify_trim, render_markdown_report
from kia_carnival.finance_checklist import (
    CHECKLIST_DISCLAIMER_BANNER,
    generate_kfa_finance_checklist,
)

SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_b"


class FakeNhtsaClient:
    """Deterministic offline stand-in for public NHTSA vPIC & Recalls APIs."""

    VIN_MAP: dict[str, dict[str, Any]] = {
        "KNDNC5H39R6300001": {
            "Make": "KIA",
            "Model": "Carnival",
            "ModelYear": "2024",
            "Trim": "EX",
            "Series": "EX 8-Passenger",
            "Seats": "8",
        },
        "KNDNE5H35P6200002": {
            "Make": "KIA",
            "Model": "Carnival",
            "ModelYear": "2023",
            "Trim": "SX Prestige",
            "Series": "VIP Lounge",
            "Seats": "7",
        },
        "KNDNE5H31P6200003": {
            "Make": "KIA",
            "Model": "Carnival",
            "ModelYear": "2023",
            "Trim": "SX",
            "Series": "SX",
            "Seats": "8",
        },
        "KNDNC5H37N6100004": {
            "Make": "KIA",
            "Model": "Carnival",
            "ModelYear": "2022",
            "Trim": "EX",
            "Series": "EX",
            "Seats": "8",
        },
        "5FNRL6H78MB000005": {
            "Make": "HONDA",
            "Model": "Odyssey",
            "ModelYear": "2021",
            "Trim": "EX-L",
            "Series": "",
            "Seats": "8",
        },
    }

    def decode_vin_values(self, vin: str) -> dict[str, Any]:
        return self.VIN_MAP.get(vin.upper(), {})

    def fetch_recalls_by_vehicle(self, make: str, model: str, model_year: int) -> list[dict[str, Any]]:
        if make.lower() == "kia" and model.lower() == "carnival" and model_year in (2022, 2023):
            return [
                {
                    "NHTSACampaignNumber": "23V144000",
                    "ManufacturerRecallNumber": "SC266",
                    "Component": "STRUCTURE:BODY:DOOR:SLIDING",
                    "Summary": "Kia Motors America SC266 power sliding door auto-reverse safety recall.",
                }
            ]
        return []


def _extract_imported_roots(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_b4_ast_strict_import_isolation() -> None:
    """Enforces ZERO imports between kia_carnival and B1/B2/B3 in BOTH directions."""
    other_modules = {"manifest_roi", "hibid_churn", "land_scorer"}

    # 1. kia_carnival MUST NOT import any of manifest_roi, hibid_churn, land_scorer
    kia_files = list((AUCTION_DIR / "kia_carnival").glob("*.py"))
    assert kia_files, "Expected Python files inside auction-intel-v2/kia_carnival/"
    for py_file in kia_files:
        imported = _extract_imported_roots(py_file)
        assert imported.isdisjoint(other_modules), (
            f"Isolation breach in {py_file.name}: imports {imported & other_modules}"
        )

    # 2. manifest_roi, hibid_churn, land_scorer MUST NOT import kia_carnival
    for pkg in other_modules:
        for py_file in (AUCTION_DIR / pkg).glob("*.py"):
            imported = _extract_imported_roots(py_file)
            assert "kia_carnival" not in imported, (
                f"Isolation breach in {pkg}/{py_file.name}: imports kia_carnival"
            )


def test_flags_vip_lounge_and_sc266_open_vin_from_synthetic_fixtures() -> None:
    payload = json.loads((SYNTH_DIR / "kia_carnival_listings_sample.json").read_text(encoding="utf-8"))
    contract_text = (SYNTH_DIR / "kia_contract_sample.txt").read_text(encoding="utf-8")

    report = check_listings(
        payload["listings"],
        client=FakeNhtsaClient(),
        contract_text=contract_text,
    )
    assert report["mode"] == "MONITOR_ONLY"
    assert report["strictly_separate_from_general_auctions"] is True
    assert report["counts"]["vip_lounge_flagged_out"] == 1
    assert report["counts"]["sc266_open_flagged"] == 1

    by_id = {item["listing_id"]: item for item in report["listings"]}

    # Clean 2024 EX with SC266 completed
    assert by_id["CARN-001"]["overall_verdict"] == "PASS_MONITOR_CANDIDATE"
    assert by_id["CARN-001"]["trim_filter"]["trim_verdict"] == "PASS"
    assert by_id["CARN-001"]["recall_check"]["sc266_status"] == "SC266_COMPLETED"

    # VIP Lounge / SX Prestige flagged out
    assert by_id["CARN-002"]["overall_verdict"] == "FLAGGED_OUT_VIP_LOUNGE"
    assert by_id["CARN-002"]["trim_filter"]["trim_verdict"] == "FLAGGED_OUT_VIP_LOUNGE"

    # 2023 SX 8-passenger passes trim but SC266 is OPEN => flagged
    assert by_id["CARN-003"]["trim_filter"]["trim_verdict"] == "PASS"
    assert by_id["CARN-003"]["recall_check"]["sc266_status"] == "SC266_OPEN"
    assert by_id["CARN-003"]["overall_verdict"] == "FLAG_RECALL_SC266_OPEN"
    assert (
        by_id["CARN-003"]["recall_check"]["nhtsa_vin_recall_url"]
        == "https://www.nhtsa.gov/recalls?vin=KNDNE5H31P6200003"
    )

    # 2022 EX with no VIN-level status => model-year SC266 verify prompt + direct NHTSA URL
    assert by_id["CARN-004"]["recall_check"]["sc266_status"] == "SC266_MODEL_YEAR_APPLICABLE_VERIFY_VIN"
    assert by_id["CARN-004"]["overall_verdict"] == "REVIEW_VERIFY_SC266_OR_TRIM"

    # Non-Kia 2021 Odyssey rejected
    assert by_id["OTHER-005"]["overall_verdict"] == "REJECT_WRONG_VEHICLE"

    # C-3 compliance: KFA finance checklist explicitly labelled document checklist generator only
    checklist = report["kfa_summer_2027_finance_checklist"]
    assert checklist["banner"] == CHECKLIST_DISCLAIMER_BANNER
    assert "DOCUMENT CHECKLIST GENERATOR ONLY" in checklist["banner"]
    assert "NOT LEGAL OR FINANCIAL ADVICE" in checklist["banner"]
    assert checklist["is_legal_or_financial_advice"] is False

    by_clause = {c["clause_id"]: c for c in checklist["checklist_items"]}
    assert by_clause["ZERO_PREPAYMENT_PENALTY"]["status"] == "FAVORABLE_PHRASE_FOUND"
    assert by_clause["SIMPLE_INTEREST_DAILY_ACCRUAL"]["status"] == "FAVORABLE_PHRASE_FOUND"
    assert by_clause["DEALER_CHARGEBACK_VS_BORROWER_OBLIGATION"]["status"] == "RISK_PHRASE_FOUND"

    md = render_markdown_report(report)
    assert CHECKLIST_DISCLAIMER_BANNER in md
    assert "FLAGGED_OUT_VIP_LOUNGE" in md
    assert "SC266_OPEN" in md


def test_blank_kfa_checklist_and_trim_edge_cases() -> None:
    blank = generate_kfa_finance_checklist(None)
    assert blank["contract_text_scanned"] is False
    assert blank["banner"] == CHECKLIST_DISCLAIMER_BANNER
    assert len(blank["checklist_items"]) == 4
    assert all(i["status"] == "NEEDS_MANUAL_REVIEW" for i in blank["checklist_items"])

    assert classify_trim(listing_title="2023 Kia Carnival SX 8-Passenger")["trim_verdict"] == "PASS"
    assert (
        classify_trim(listing_title="2024 Kia Carnival w/ VIP Lounge Seat Package")["trim_verdict"]
        == "FLAGGED_OUT_VIP_LOUNGE"
    )
    assert classify_trim(listing_title="2023 Kia Carnival LX")["trim_verdict"] == "MANUAL_TRIM_CHECK"
