"""Read-only adapters for loading NC land parcel candidates from JSON, CSV, or public county HTML feeds.

Strictly read-only (HTTP GET only when fetching public county pages; never submits
forms, creates accounts, or bypasses anti-bot challenges).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = "TossonEnvironmentalAnalytics-LandResearchBot/2.0 (read-only public records)"


def load_parcels_from_json(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return list(payload.get("parcels") or payload.get("listings") or payload.get("items") or [])
    if isinstance(payload, list):
        return list(payload)
    raise ValueError(f"Unsupported JSON parcel root in {p}")


def load_parcels_from_csv(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def parse_county_tax_auction_html(
    html_text: str,
    *,
    base_url: str = "",
    default_county: str = "",
    default_state: str = "NC",
    source_name: str = "county_public_html",
) -> list[dict[str, Any]]:
    """Parse a public county GIS / tax-auction HTML table into canonical parcel dicts.

    Supports tables with header columns such as Parcel ID / PIN, County, Acres / Acreage,
    Opening Bid / Price, Road Frontage, Zoning, Lat/Lon, and a direct `<a href>` parcel link.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find("table")
    if table is None:
        return []

    header_cells = table.find_all("th")
    headers = [cell.get_text(" ", strip=True).lower() for cell in header_cells]
    rows = table.find_all("tr")

    records: list[dict[str, Any]] = []
    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue
        row_map: dict[str, str] = {}
        direct_href = ""
        for idx, td in enumerate(tds):
            col_name = headers[idx] if idx < len(headers) else f"col_{idx}"
            row_map[col_name] = td.get_text(" ", strip=True)
            anchor = td.find("a", href=True)
            if anchor and not direct_href:
                href = str(anchor["href"]).strip()
                direct_href = urljoin(base_url, href) if base_url else href

        def _pick(*keys: str) -> str:
            for k in keys:
                for hk, hv in row_map.items():
                    if k in hk and hv != "":
                        return hv
            return ""

        records.append(
            {
                "parcel_id": _pick("parcel", "pin", "lot", "id"),
                "title": _pick("description", "address", "title", "location") or _pick("parcel", "pin"),
                "county": _pick("county") or default_county,
                "state": _pick("state") or default_state,
                "acreage": _pick("acre", "size"),
                "price": _pick("price", "opening bid", "bid", "min bid", "amount"),
                "road_frontage": _pick("road", "frontage", "access"),
                "zoning": _pick("zoning", "zone", "land use"),
                "lat": _pick("lat"),
                "lon": _pick("lon", "lng"),
                "url": direct_href or _pick("url", "link"),
                "source": source_name,
            }
        )
    return records


def fetch_public_feed_html(
    url: str,
    *,
    timeout: int = 15,
    user_agent: str = DEFAULT_USER_AGENT,
    session: Any | None = None,
) -> str:
    """Read-only HTTP GET for public county GIS / tax-auction HTML pages."""
    client = session if session is not None else requests
    resp = client.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def load_parcels_from_file(
    path: Path | str,
    *,
    base_url: str = "",
    default_county: str = "",
) -> list[dict[str, Any]]:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".json":
        return load_parcels_from_json(p)
    if ext == ".csv":
        return load_parcels_from_csv(p)
    if ext in {".html", ".htm"}:
        return parse_county_tax_auction_html(
            p.read_text(encoding="utf-8"),
            base_url=base_url,
            default_county=default_county,
            source_name=p.name,
        )
    raise ValueError(f"Unsupported parcel input file extension: {p}")
