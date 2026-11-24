"""B1 — Read-only Manifest ROI Analyser for Liquidation.com and B-Stock CSVs."""
from __future__ import annotations

from .adapters import ManifestItem, ManifestLot, detect_format, parse_manifest_csv
from .analyser import analyse_manifest, load_roi_rules, load_sold_history, render_markdown_report

__all__ = [
    "ManifestItem",
    "ManifestLot",
    "analyse_manifest",
    "detect_format",
    "load_roi_rules",
    "load_sold_history",
    "parse_manifest_csv",
    "render_markdown_report",
]
