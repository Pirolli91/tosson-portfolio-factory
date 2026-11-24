"""Build A6: Live Seed JD Capture from Official Employer Career Pages Only.

Standing rules enforced:
- Fetches official employer career pages ONLY (never aggregators, never reconstructed from memory).
- Never bypasses CAPTCHAs, Cloudflare challenges, or anti-bot gates.
- Records exact canonical URL, HTTP status, UTC timestamp, and honest capture status:
  - OPEN                 : HTTP 200 with readable official job description text
  - CLOSED               : HTTP 404/410 or explicit closed/expired notice on official page
  - UNFETCHABLE_BOT_GATE : HTTP 403/429 or anti-bot / JS / CAPTCHA gate encountered
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests
import yaml
from bs4 import BeautifulSoup

GAP_DIR = Path(__file__).resolve().parent
DEFAULT_SEED_CONFIG = GAP_DIR / "seed_jds.yaml"
DEFAULT_SNAPSHOTS_DIR = GAP_DIR / "snapshots"

USER_AGENT = "TossonEnvironmentalAnalytics/1.0 (public-career-page-read-only-research)"

CLOSED_MARKERS = [
    re.compile(r"\bjob\s+(?:is\s+)?no\s+longer\s+(?:available|open|active)\b", re.I),
    re.compile(r"\bposition\s+has\s+been\s+(?:filled|closed)\b", re.I),
    re.compile(r"\bposting\s+(?:has\s+)?expired\b", re.I),
    re.compile(r"\bpage\s+not\s+found\b", re.I),
    re.compile(r"\bthis\s+requisition\s+is\s+closed\b", re.I),
]

BOT_GATE_MARKERS = [
    re.compile(r"<title>\s*just\s+a\s+moment", re.I),
    re.compile(r"\bcloudflare\b.*\bchallenge\b", re.I),
    re.compile(r"\b(?:captcha|recaptcha|hcaptcha|turnstile)\b", re.I),
    re.compile(r"\baccess\s+denied\b", re.I),
    re.compile(r"\btoo\s+many\s+requests\b", re.I),
    re.compile(r"\benable\s+javascript\s+and\s+cookies\s+to\s+continue\b", re.I),
]


def _extract_visible_text(html_body: str) -> str:
    soup = BeautifulSoup(html_body, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def classify_http_response(status_code: int, body: str) -> tuple[str, str, str]:
    """Return (status, reason, extracted_text)."""
    if status_code in (404, 410):
        return "CLOSED", f"Official career page returned HTTP {status_code}.", ""

    if status_code in (403, 429, 503):
        return (
            "UNFETCHABLE_BOT_GATE",
            f"Official career page returned HTTP {status_code} (anti-bot or rate-limit gate; not bypassed).",
            "",
        )

    for rx in BOT_GATE_MARKERS:
        if rx.search(body):
            return (
                "UNFETCHABLE_BOT_GATE",
                f"Anti-bot / challenge marker detected on HTTP {status_code} response (not bypassed).",
                "",
            )

    text = _extract_visible_text(body)
    for rx in CLOSED_MARKERS:
        if rx.search(text):
            return "CLOSED", "Official career page indicates posting is closed or unavailable.", ""

    if status_code == 200 and len(text) >= 200:
        return "OPEN", "Captured live from official career page (HTTP 200).", text

    return (
        "UNFETCHABLE_BOT_GATE",
        f"HTTP {status_code} returned insufficient readable text ({len(text)} chars; likely JS-gated).",
        "",
    )


def capture_seed_jds(
    *,
    config_path: Path = DEFAULT_SEED_CONFIG,
    out_dir: Path = DEFAULT_SNAPSHOTS_DIR,
    fetcher: Callable[[str], tuple[int, str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Fetch all configured official seed JDs and write JSON snapshots."""
    with Path(config_path).open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    seeds = cfg.get("seed_jds", [])

    def _default_fetch(url: str) -> tuple[int, str, str]:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=25,
            allow_redirects=True,
        )
        return resp.status_code, resp.url, resp.text

    fetch_fn = fetcher or _default_fetch
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    captured: list[dict[str, Any]] = []
    for seed in seeds:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = seed["official_url"]
        try:
            http_status, final_url, body = fetch_fn(url)
            status, reason, text = classify_http_response(http_status, body)
        except Exception as exc:
            http_status = 0
            final_url = url
            status = "UNFETCHABLE_BOT_GATE"
            reason = f"Network/HTTP error during read-only fetch: {type(exc).__name__}: {exc}"
            text = ""

        record = {
            "jd_id": seed["jd_id"],
            "company": seed["company"],
            "role_title": seed["role_title"],
            "req_id": seed["req_id"],
            "role_family": seed.get("role_family", "Data Analyst"),
            "target_role_weight": float(seed.get("target_role_weight", 1.0)),
            "official_url": url,
            "canonical_url": final_url,
            "http_status": http_status,
            "captured_at_utc": ts,
            "status": status,
            "status_reason": reason,
            "text_length": len(text),
            "text": text,
        }
        snap_path = out_dir / f"{seed['jd_id']}.json"
        snap_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        captured.append(record)

    manifest = {
        "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(captured),
        "records": [
            {k: v for k, v in rec.items() if k != "text"} for rec in captured
        ],
    }
    (out_dir / "capture_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return captured


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live capture of official seed JDs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_SEED_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_SNAPSHOTS_DIR)
    args = parser.parse_args(argv)
    recs = capture_seed_jds(config_path=args.config, out_dir=args.out_dir)
    print(
        json.dumps(
            [{k: v for k, v in r.items() if k != "text"} for r in recs],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
