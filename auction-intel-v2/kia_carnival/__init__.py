"""B4 — STRICTLY SEPARATE Kia Carnival (2022+) Checker — Monitor Mode Only.

Total architectural isolation: ZERO imports from or into manifest_roi,
hibid_churn, or land_scorer.
"""
from __future__ import annotations

from .checker import (
    HttpNhtsaClient,
    NhtsaClientProtocol,
    check_listings,
    check_sc266_recall,
    classify_trim,
    decode_vin,
    render_markdown_report,
)
from .finance_checklist import (
    CHECKLIST_DISCLAIMER_BANNER,
    generate_kfa_finance_checklist,
    render_checklist_markdown,
)

__all__ = [
    "CHECKLIST_DISCLAIMER_BANNER",
    "HttpNhtsaClient",
    "NhtsaClientProtocol",
    "check_listings",
    "check_sc266_recall",
    "classify_trim",
    "decode_vin",
    "generate_kfa_finance_checklist",
    "render_checklist_markdown",
    "render_markdown_report",
]
