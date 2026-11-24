"""B4 — STRICTLY SEPARATE Kia Carnival (2022+) Listing & Recall Checker.

Monitor mode ONLY (read-only). NEVER merged into manifest_roi, hibid_churn, or
land_scorer — zero imports to or from those modules.

Checks:
1. Public NHTSA vPIC VIN decode (`DecodeVinValues`) verifying Make==KIA, Model==Carnival, ModelYear>=2022.
2. Public NHTSA Recalls API (`recallsByVehicle`) specifically checking Kia SC266 / NHTSA 23V144000
   (power sliding door) + injectable VIN-level recall status, always emitting direct URL
   `https://www.nhtsa.gov/recalls?vin=<VIN>`.
3. Trim filter: EX / SX (8-passenger) -> PASS; SX Prestige / VIP Lounge -> FLAGGED_OUT_VIP_LOUNGE.
4. Summer-2027 KFA finance-clause checklist stub (DOCUMENT CHECKLIST GENERATOR ONLY — NOT LEGAL OR FINANCIAL ADVICE).
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import requests

try:
    from .finance_checklist import (
        CHECKLIST_DISCLAIMER_BANNER,
        generate_kfa_finance_checklist,
        render_checklist_markdown,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from finance_checklist import (
        CHECKLIST_DISCLAIMER_BANNER,
        generate_kfa_finance_checklist,
        render_checklist_markdown,
    )

LEGAL_ENTITY = "Tosson Services LLC dba Tosson Environmental Analytics"
VPIC_DECODE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
NHTSA_RECALLS_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"
NHTSA_VIN_RECALL_DIRECT_URL = "https://www.nhtsa.gov/recalls?vin={vin}"
DEFAULT_USER_AGENT = "TossonEnvironmentalAnalytics-KiaMonitor/2.0 (read-only NHTSA lookup)"

VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
SC266_CAMPAIGN_ID = "23V144000"

VIP_LOUNGE_PATTERNS = (
    re.compile(r"\bsx[\s\-]*prestige\b", re.IGNORECASE),
    re.compile(r"\bsxp\b", re.IGNORECASE),
    re.compile(r"\bvip\s+lounge\b", re.IGNORECASE),
    re.compile(r"\blounge\s+seat(s|ing)?\b", re.IGNORECASE),
    re.compile(r"\b7[\s\-]*(pass(enger)?|seat)\s*(vip|lounge)?\b", re.IGNORECASE),
    re.compile(r"\breclining\s+second[\s\-]*row\s+lounge\b", re.IGNORECASE),
)

PASS_TRIM_PATTERNS = (
    re.compile(r"\bex\b", re.IGNORECASE),
    re.compile(r"\bsx\b(?!\s*prestige\b)", re.IGNORECASE),
)


class NhtsaClientProtocol(Protocol):
    def decode_vin_values(self, vin: str) -> dict[str, Any]:
        ...

    def fetch_recalls_by_vehicle(self, make: str, model: str, model_year: int) -> list[dict[str, Any]]:
        ...


class HttpNhtsaClient:
    """Default read-only HTTP client for public domain NHTSA vPIC & Recalls APIs."""

    def __init__(self, *, timeout: int = 15, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def decode_vin_values(self, vin: str) -> dict[str, Any]:
        url = VPIC_DECODE_URL.format(vin=vin)
        resp = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("Results") or []
        return results[0] if results else {}

    def fetch_recalls_by_vehicle(self, make: str, model: str, model_year: int) -> list[dict[str, Any]]:
        resp = requests.get(
            NHTSA_RECALLS_URL,
            params={"make": make.lower(), "model": model.lower(), "modelYear": str(model_year)},
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        return list(payload.get("results") or payload.get("Results") or [])


def is_valid_vin_format(vin: str) -> bool:
    return bool(VIN_PATTERN.match(vin.strip().upper()))


def decode_vin(vin: str, *, client: NhtsaClientProtocol) -> dict[str, Any]:
    """Decode a 17-character VIN via NHTSA vPIC and validate 2022+ Kia Carnival."""
    clean_vin = vin.strip().upper()
    if not is_valid_vin_format(clean_vin):
        return {
            "vin": clean_vin,
            "vin_format_valid": False,
            "is_target_2022_plus_kia_carnival": False,
            "make": "",
            "model": "",
            "model_year": None,
            "trim": "",
            "series": "",
            "seats": "",
            "validation_notes": ["Invalid 17-character VIN format"],
        }

    raw = client.decode_vin_values(clean_vin)
    make = str(raw.get("Make") or "").strip()
    model = str(raw.get("Model") or "").strip()
    year_str = str(raw.get("ModelYear") or "").strip()
    model_year = int(year_str) if year_str.isdigit() else None
    trim = str(raw.get("Trim") or "").strip()
    series = str(raw.get("Series") or "").strip()
    seats = str(raw.get("Seats") or "").strip()

    notes: list[str] = []
    make_ok = make.upper() == "KIA"
    model_ok = "CARNIVAL" in model.upper()
    year_ok = model_year is not None and model_year >= 2022
    if not make_ok:
        notes.append(f"Make is '{make or 'MISSING'}' (expected KIA)")
    if not model_ok:
        notes.append(f"Model is '{model or 'MISSING'}' (expected Carnival)")
    if not year_ok:
        notes.append(f"ModelYear is '{model_year}' (expected >= 2022)")

    return {
        "vin": clean_vin,
        "vin_format_valid": True,
        "is_target_2022_plus_kia_carnival": bool(make_ok and model_ok and year_ok),
        "make": make,
        "model": model,
        "model_year": model_year,
        "trim": trim,
        "series": series,
        "seats": seats,
        "vpic_source_url": VPIC_DECODE_URL.format(vin=clean_vin),
        "validation_notes": notes,
    }


def _is_sc266_recall_record(rec: dict[str, Any]) -> bool:
    campaign = str(rec.get("NHTSACampaignNumber") or rec.get("campaignNumber") or "").upper()
    component = str(rec.get("Component") or "").lower()
    summary = str(rec.get("Summary") or "").lower()
    mfr_code = str(rec.get("ManufacturerRecallNumber") or rec.get("manufacturerCode") or "").upper()
    if SC266_CAMPAIGN_ID in campaign or "SC266" in mfr_code or "SC266" in summary.upper():
        return True
    if "sliding door" in component or ("power sliding door" in summary and "auto-reverse" in summary):
        return True
    return False


def check_sc266_recall(
    vin: str,
    model_year: int | None,
    *,
    client: NhtsaClientProtocol,
    vin_recall_status: str | None = None,
) -> dict[str, Any]:
    """Check NHTSA recalls for Kia SC266 / 23V144000 (power sliding door) + VIN status."""
    clean_vin = vin.strip().upper()
    direct_url = NHTSA_VIN_RECALL_DIRECT_URL.format(vin=clean_vin)

    recalls: list[dict[str, Any]] = []
    if model_year is not None:
        recalls = client.fetch_recalls_by_vehicle("kia", "carnival", model_year)

    sc266_matches = [r for r in recalls if _is_sc266_recall_record(r)]
    model_year_has_sc266 = len(sc266_matches) > 0

    normalized_vin_status = (vin_recall_status or "").strip().upper()
    if normalized_vin_status in {"OPEN", "SC266_OPEN", "INCOMPLETE", "UNREMEDIED"}:
        sc266_status = "SC266_OPEN"
        flagged = True
    elif normalized_vin_status in {"COMPLETED", "SC266_COMPLETED", "REMEDIED", "CLOSED"}:
        sc266_status = "SC266_COMPLETED"
        flagged = False
    elif model_year_has_sc266:
        sc266_status = "SC266_MODEL_YEAR_APPLICABLE_VERIFY_VIN"
        flagged = True
    else:
        sc266_status = "SC266_NOT_LISTED_FOR_MODEL_YEAR"
        flagged = False

    return {
        "vin": clean_vin,
        "model_year": model_year,
        "total_model_year_recalls": len(recalls),
        "model_year_sc266_applicable": model_year_has_sc266,
        "sc266_campaign_numbers": sorted(
            {
                str(r.get("NHTSACampaignNumber") or r.get("campaignNumber") or SC266_CAMPAIGN_ID)
                for r in sc266_matches
            }
        ),
        "vin_recall_status_input": normalized_vin_status or None,
        "sc266_status": sc266_status,
        "sc266_flag": flagged,
        "nhtsa_vin_recall_url": direct_url,
    }


def classify_trim(
    *,
    decoded_trim: str = "",
    decoded_series: str = "",
    decoded_seats: str = "",
    listing_title: str = "",
    listing_description: str = "",
) -> dict[str, Any]:
    """Filter trims: EX / SX (8-passenger) -> PASS; SX Prestige / VIP Lounge -> FLAGGED_OUT_VIP_LOUNGE."""
    combined = " | ".join(
        part.strip()
        for part in (decoded_trim, decoded_series, listing_title, listing_description)
        if part and part.strip()
    )

    # Check VIP Lounge / SX Prestige disqualifiers FIRST
    for pat in VIP_LOUNGE_PATTERNS:
        m = pat.search(combined)
        if m:
            return {
                "trim_verdict": "FLAGGED_OUT_VIP_LOUNGE",
                "matched_signal": m.group(0),
                "reason": "VIP Lounge / SX Prestige 7-passenger second-row seats excluded per owner criteria.",
            }

    if decoded_seats.strip() == "7" and "vip" in combined.lower():
        return {
            "trim_verdict": "FLAGGED_OUT_VIP_LOUNGE",
            "matched_signal": "7-seat VIP",
            "reason": "7-passenger VIP Lounge configuration excluded per owner criteria.",
        }

    # Next check EX or non-Prestige SX
    for pat in PASS_TRIM_PATTERNS:
        m = pat.search(combined)
        if m:
            return {
                "trim_verdict": "PASS",
                "matched_signal": m.group(0).upper(),
                "reason": "Target EX / SX 8-passenger trim detected (no VIP Lounge indicators).",
            }

    return {
        "trim_verdict": "MANUAL_TRIM_CHECK",
        "matched_signal": "",
        "reason": "Trim not conclusively identified as EX/SX or VIP Lounge; inspect window sticker / 2nd-row seat photos.",
    }


def check_listings(
    listings: list[dict[str, Any]],
    *,
    client: NhtsaClientProtocol | None = None,
    contract_text: str | None = None,
) -> dict[str, Any]:
    """Evaluate 2022+ Kia Carnival candidate listings in monitor-only mode."""
    nhtsa_client = client if client is not None else HttpNhtsaClient()
    results: list[dict[str, Any]] = []

    for idx, item in enumerate(listings):
        listing_id = str(item.get("listing_id") or f"KIA-{idx + 1}").strip()
        vin = str(item.get("vin") or "").strip().upper()
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        price = item.get("price")
        mileage = item.get("mileage")
        listing_url = str(item.get("url") or "").strip()
        vin_recall_status = item.get("sc266_vin_status") or item.get("vin_recall_status")

        decoded = decode_vin(vin, client=nhtsa_client)
        recall = check_sc266_recall(
            vin,
            decoded["model_year"],
            client=nhtsa_client,
            vin_recall_status=str(vin_recall_status) if vin_recall_status else None,
        )
        trim_info = classify_trim(
            decoded_trim=decoded["trim"],
            decoded_series=decoded["series"],
            decoded_seats=decoded["seats"],
            listing_title=title,
            listing_description=description,
        )

        if not decoded["is_target_2022_plus_kia_carnival"]:
            overall = "REJECT_WRONG_VEHICLE"
        elif trim_info["trim_verdict"] == "FLAGGED_OUT_VIP_LOUNGE":
            overall = "FLAGGED_OUT_VIP_LOUNGE"
        elif recall["sc266_status"] == "SC266_OPEN":
            overall = "FLAG_RECALL_SC266_OPEN"
        elif trim_info["trim_verdict"] == "MANUAL_TRIM_CHECK" or recall["sc266_flag"]:
            overall = "REVIEW_VERIFY_SC266_OR_TRIM"
        else:
            overall = "PASS_MONITOR_CANDIDATE"

        results.append(
            {
                "listing_id": listing_id,
                "vin": vin,
                "title": title,
                "price": price,
                "mileage": mileage,
                "listing_url": listing_url,
                "overall_verdict": overall,
                "vin_decode": decoded,
                "recall_check": recall,
                "trim_filter": trim_info,
            }
        )

    checklist = generate_kfa_finance_checklist(contract_text)

    verdict_counts: dict[str, int] = {}
    for r in results:
        v = r["overall_verdict"]
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    return {
        "module": "b4-kia-carnival-checker",
        "mode": "MONITOR_ONLY",
        "strictly_separate_from_general_auctions": True,
        "legal_entity": LEGAL_ENTITY,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_urls": [
            "https://vpic.nhtsa.dot.gov/api/",
            "https://api.nhtsa.gov/recalls/recallsByVehicle",
        ],
        "counts": {
            "total_evaluated": len(results),
            "by_verdict": verdict_counts,
            "vip_lounge_flagged_out": sum(
                1 for r in results if r["trim_filter"]["trim_verdict"] == "FLAGGED_OUT_VIP_LOUNGE"
            ),
            "sc266_open_flagged": sum(
                1 for r in results if r["recall_check"]["sc266_status"] == "SC266_OPEN"
            ),
        },
        "listings": results,
        "kfa_summer_2027_finance_checklist": checklist,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    c = report["counts"]
    lines: list[str] = [
        "# B4 — Kia Carnival (2022+) Checker Report (Isolated Monitor Mode)",
        "",
        f"- **Entity:** {report['legal_entity']}",
        f"- **Execution Mode:** `{report['mode']}` (strictly separate from general auction modules B1–B3; no buying, bidding, or dealer inquiries)",
        f"- **Listings Evaluated:** `{c['total_evaluated']}`",
        f"- **VIP Lounge Flagged Out:** `{c['vip_lounge_flagged_out']}`",
        f"- **SC266 Open VINs Flagged:** `{c['sc266_open_flagged']}`",
        f"- **Generated (UTC):** `{report['generated_at']}`",
        "",
        "## Evaluated Listings",
        "",
        "| Listing ID | Year / Model | VIN | Trim Filter | SC266 Recall Status | Overall Verdict | NHTSA VIN Recall Link |",
        "|---|---|---|---|---|---|---|",
    ]

    for item in report["listings"]:
        dec = item["vin_decode"]
        rec = item["recall_check"]
        trm = item["trim_filter"]
        ym = f"{dec['model_year'] or '?'} {dec['make']} {dec['model']}".strip()
        lines.append(
            f"| `{item['listing_id']}` | {ym} | `{item['vin']}` | "
            f"`{trm['trim_verdict']}` | `{rec['sc266_status']}` | **{item['overall_verdict']}** | "
            f"[Check VIN on NHTSA]({rec['nhtsa_vin_recall_url']}) |"
        )

    lines.extend(["", "### Listing Details", ""])
    for item in report["listings"]:
        trm = item["trim_filter"]
        rec = item["recall_check"]
        lines.append(
            f"- **`{item['listing_id']}` ({item['title']})** — Verdict: `{item['overall_verdict']}` | "
            f"Trim: `{trm['trim_verdict']}` ({trm['reason']}) | "
            f"SC266: `{rec['sc266_status']}` (`{rec['nhtsa_vin_recall_url']}`)"
        )

    lines.extend(["", render_checklist_markdown(report["kfa_summer_2027_finance_checklist"])])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=f"B4 Isolated Kia Carnival Checker (Monitor Mode Only). {CHECKLIST_DISCLAIMER_BANNER}."
    )
    parser.add_argument("--input", required=True, help="JSON file containing candidate Kia Carnival listings")
    parser.add_argument("--contract-text", default=None, help="Optional text file with KFA finance contract text to scan")
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-md", default=None)

    args = parser.parse_args(argv)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    listings = payload["listings"] if isinstance(payload, dict) else list(payload)
    contract_txt = Path(args.contract_text).read_text(encoding="utf-8") if args.contract_text else None

    report = check_listings(listings, contract_text=contract_txt)
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
