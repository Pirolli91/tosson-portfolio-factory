"""Build A5: Deterministic Packet Claim-Verifier with Negation/Disavowal Awareness.

Verifies skill and experience claims in a job-application packet (resume + cover
letter in .docx, .txt, or .md) against:
  1. Forbidden-claim rules (forbidden_rules.yaml)
  2. Proof Registry (proof-registry.json — runnable portfolio artifacts)
  3. Owner's base documents (injectable --base-docs file or directory)

Verdicts per claim:
  - FORBIDDEN              : violates standing rules (citizenship, clearance, proprietary material, UCMR 5 "violation")
  - PROVEN_BY_ARTIFACT     : backed by a verified entry in proof-registry.json (emits artifact_id)
  - IN_BASE_DOCS           : positively present in base documents (emits file + excerpt)
  - DISAVOWED_HONEST_GAP   : explicitly disavowed / honest-candor omission (never misread as positive claim)
  - UNSUPPORTED            : positively claimed in packet without registry or base-doc backing

Read-only tool: never submits, sends, or modifies input documents.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup
from docx import Document

VERIFIER_DIR = Path(__file__).resolve().parent
REPO_ROOT = VERIFIER_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from shared.proof_registry import DEFAULT_REGISTRY_PATH, load_registry

DEFAULT_TAXONOMY_PATH = VERIFIER_DIR / "skill_taxonomy.yaml"
DEFAULT_FORBIDDEN_PATH = VERIFIER_DIR / "forbidden_rules.yaml"

SUPPORTED_EXTS = {".txt", ".md", ".docx"}

# Prefix triggers disavow skills occurring AFTER the trigger in the same clause.
PREFIX_DISAVOWAL_REGEXES = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\brather\s+than\b",
        r"\binstead\s+of\b",
        r"\bhave\s+not\s+(?:yet\s+)?(?:worked|used|built|administered|deployed|managed|operated)\b",
        r"\bhaven't\s+(?:yet\s+)?(?:worked|used|built|administered|deployed|managed|operated)\b",
        r"\bnot\s+(?:yet\s+)?(?:worked|experienced|familiar|proficient)\s+with\b",
        r"\bno\s+(?:direct\s+|prior\s+|hands-on\s+)?(?:experience|background|exposure)\s+(?:with|in)\b",
        r"\bdo\s+not\s+(?:claim|have|use|want\s+the\s+resume\s+to\s+imply)\b",
        r"\bdon't\s+(?:claim|have|use)\b",
        r"\boutside\s+my\s+(?:current\s+)?(?:stack|experience|background)\b",
        r"\bnot\s+executed\s+against\b",
        r"\bnot\s+currently\s+using\b",
        r"\bwithout\s+prior\b",
        r"\bunlike\b",
    )
]

# Suffix triggers disavow skills occurring BEFORE the trigger in the same clause.
SUFFIX_DISAVOWAL_REGEXES = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^\s*-comparable\b",
        r"\bcomparable\s+to\b",
        r"\bwould\s+be\s+new\s+ground\b",
        r"\bis\s+new\s+ground\b",
        r"\bhave\s+not\s+been\s+part\s+of\s+my\b",
        r"\bhas\s+not\s+been\s+part\s+of\s+my\b",
        r"\bis\s+not\s+part\s+of\s+my\b",
        r"\bare\s+not\s+part\s+of\s+my\b",
        r"\b(?:is|are)\s+outside\s+my\s+(?:current\s+)?(?:stack|experience)\b",
    )
]


def read_document_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".docx":
        doc = Document(str(path))
        parts: list[str] = []
        for p in doc.paragraphs:
            if p.text.strip():
                parts.append(p.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_txt = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_txt:
                    parts.append(row_txt)
        return "\n".join(parts)
    return path.read_text(encoding="utf-8", errors="replace")


def load_documents(path_or_dir: Path | str | None) -> list[tuple[str, str]]:
    """Return list of (label, text) from a file or directory."""
    if path_or_dir is None:
        return []
    p = Path(path_or_dir)
    if not p.exists():
        return []
    docs: list[tuple[str, str]] = []
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_EXTS:
            docs.append((p.name, read_document_text(p)))
        return docs
    for child in sorted(p.rglob("*")):
        if child.is_file() and child.suffix.lower() in SUPPORTED_EXTS:
            rel = str(child.relative_to(p))
            docs.append((rel, read_document_text(child)))
    return docs


def load_jd_text(jd_arg: str | None) -> tuple[str | None, str | None]:
    """Load JD text from local file path or HTTP(S) URL. Returns (source_label, text)."""
    if not jd_arg:
        return None, None
    if jd_arg.startswith(("http://", "https://")):
        resp = requests.get(
            jd_arg,
            headers={"User-Agent": "TossonEnvironmentalAnalytics/1.0 (jd-verifier)"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return jd_arg, soup.get_text("\n", strip=True)
    p = Path(jd_arg)
    if not p.exists():
        raise FileNotFoundError(f"JD file not found: {p}")
    return p.name, read_document_text(p)


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Split on sentence-ending punctuation followed by whitespace
        chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", line)
        for ch in chunks:
            ch = ch.strip()
            if ch:
                sentences.append(ch)
    return sentences


def _split_clauses(sentence: str) -> list[tuple[int, int, str]]:
    """Return (start, end, clause_text) split on strong clause separators (; or em-dash)."""
    spans: list[tuple[int, int, str]] = []
    last = 0
    for m in re.finditer(r"(?:\s+[—–]\s+|;\s*)", sentence):
        spans.append((last, m.start(), sentence[last : m.start()]))
        last = m.end()
    spans.append((last, len(sentence), sentence[last:]))
    return spans


def is_match_disavowed(sentence: str, match_start: int, match_end: int) -> tuple[bool, str | None]:
    """Determine if a skill match at [match_start, match_end) is honestly disavowed."""
    clause_text = sentence
    local_start = match_start
    local_end = match_end
    for c_start, c_end, c_txt in _split_clauses(sentence):
        if c_start <= match_start <= c_end:
            clause_text = c_txt
            local_start = match_start - c_start
            local_end = match_end - c_start
            break

    before = clause_text[:local_start]
    after = clause_text[local_end:]

    for rx in PREFIX_DISAVOWAL_REGEXES:
        m = rx.search(before)
        if m:
            # Ensure there isn't a hard positive pivot ("but I do use") between trigger and skill
            between = before[m.end() :]
            if not re.search(r"\b(?:but\s+i\s+(?:do|have)|however\s+i\s+(?:do|have))\b", between, re.I):
                return True, m.group(0).strip()

    for rx in SUFFIX_DISAVOWAL_REGEXES:
        m = rx.search(after)
        if m and m.start() <= 50:
            return True, m.group(0).strip()

    return False, None


def load_taxonomy(path: Path = DEFAULT_TAXONOMY_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    skills = data.get("skills", [])
    compiled: list[dict[str, Any]] = []
    for item in skills:
        canonical = item["canonical"]
        aliases = item.get("aliases", [])
        compiled_aliases = []
        for pat in aliases:
            flags = 0 if canonical == "R" and pat.startswith("(?<![a-zA-Z0-9_/])R") else re.IGNORECASE
            compiled_aliases.append(re.compile(pat, flags))
        compiled.append(
            {
                "canonical": canonical,
                "category": item.get("category", "general"),
                "patterns": compiled_aliases,
            }
        )
    return compiled


def load_forbidden_rules(path: Path = DEFAULT_FORBIDDEN_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    compiled: list[dict[str, Any]] = []
    for r in data.get("rules", []):
        compiled.append(
            {
                "id": r["id"],
                "category": r.get("category", "forbidden"),
                "severity": r.get("severity", "critical"),
                "description": r.get("description", ""),
                "allow_if_in_base_docs": bool(r.get("allow_if_in_base_docs", False)),
                "patterns": [re.compile(p) for p in r.get("patterns", [])],
                "negative_patterns": [re.compile(p) for p in r.get("negative_patterns", [])],
            }
        )
    return compiled


def extract_skill_mentions(
    docs: list[tuple[str, str]],
    taxonomy: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Extract all skill mentions across docs, avoiding span double-counting
    (e.g. 'Snowflake-dialect SQL' consumes its span before generic 'Snowflake')."""
    mentions: dict[str, list[dict[str, Any]]] = {}

    for doc_name, text in docs:
        for sentence in split_sentences(text):
            consumed_spans: list[tuple[int, int]] = []
            for skill in taxonomy:
                canonical = skill["canonical"]
                for rx in skill["patterns"]:
                    for m in rx.finditer(sentence):
                        s_idx, e_idx = m.start(), m.end()
                        # Skip if fully inside an already matched more-specific skill span
                        if any(cs <= s_idx and e_idx <= ce for cs, ce in consumed_spans):
                            continue
                        consumed_spans.append((s_idx, e_idx))
                        disavowed, trigger = is_match_disavowed(sentence, s_idx, e_idx)
                        mentions.setdefault(canonical, []).append(
                            {
                                "canonical": canonical,
                                "category": skill["category"],
                                "document": doc_name,
                                "matched_text": m.group(0),
                                "excerpt": sentence[:240],
                                "disavowed": disavowed,
                                "disavowal_trigger": trigger,
                            }
                        )
    return mentions


def _match_registry_for_skill(
    canonical: str,
    skill_meta: dict[str, Any],
    registry_entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the first registry entry that directly supports canonical skill."""
    canon_lower = canonical.lower()
    for entry in registry_entries:
        claims = entry.get("supports_claims", [])
        for claim in claims:
            c_low = claim.lower().strip()
            # Guard: dialect-only Snowflake claim MUST NOT prove unqualified 'Snowflake'
            if canonical == "Snowflake" and "dialect-only" in c_low:
                continue
            if canonical == "Snowflake" and "snowflake-dialect" in c_low:
                continue
            if c_low == canon_lower:
                return {
                    "artifact_id": entry["artifact_id"],
                    "title": entry["title"],
                    "repo_path": entry["repo_path"],
                    "matched_claim": claim,
                    "evidence_result": entry.get("evidence", {}).get("result", ""),
                }
            # Allow whole-word pattern match on supports_claims unless guarded above
            for rx in skill_meta["patterns"]:
                if rx.search(claim):
                    return {
                        "artifact_id": entry["artifact_id"],
                        "title": entry["title"],
                        "repo_path": entry["repo_path"],
                        "matched_claim": claim,
                        "evidence_result": entry.get("evidence", {}).get("result", ""),
                    }
    return None


def _check_forbidden(
    packet_docs: list[tuple[str, str]],
    base_docs: list[tuple[str, str]],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    base_text = "\n".join(txt for _, txt in base_docs)
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for doc_name, text in packet_docs:
        for sentence in split_sentences(text):
            for rule in rules:
                if any(nrx.search(sentence) for nrx in rule["negative_patterns"]):
                    continue
                for prx in rule["patterns"]:
                    m = prx.search(sentence)
                    if not m:
                        continue
                    # If allowed when explicitly backed by base docs, verify base_text
                    if rule["allow_if_in_base_docs"] and base_text:
                        if any(
                            bprx.search(bsent)
                            and not any(bnrx.search(bsent) for bnrx in rule["negative_patterns"])
                            for bsent in split_sentences(base_text)
                            for bprx in rule["patterns"]
                        ):
                            continue
                    key = (rule["id"], doc_name, m.group(0).lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(
                        {
                            "claim": f"FORBIDDEN_RULE:{rule['id']}",
                            "category": rule["category"],
                            "verdict": "FORBIDDEN",
                            "document": doc_name,
                            "matched_text": m.group(0),
                            "excerpt": sentence[:240],
                            "evidence": rule["description"],
                            "artifact_id": None,
                        }
                    )
    return findings


def verify_packet(
    *,
    packet_path: Path | str,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    base_docs_path: Path | str | None = None,
    jd_source: str | None = None,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
    forbidden_path: Path = DEFAULT_FORBIDDEN_PATH,
) -> dict[str, Any]:
    """Run deterministic claim verification and return structured report dict."""
    taxonomy = load_taxonomy(taxonomy_path)
    tax_by_name = {t["canonical"]: t for t in taxonomy}
    forbidden_rules = load_forbidden_rules(forbidden_path)

    packet_docs = load_documents(packet_path)
    if not packet_docs:
        raise FileNotFoundError(f"No supported packet documents (.docx/.txt/.md) found at {packet_path}")

    base_docs = load_documents(base_docs_path)
    registry_data = load_registry(registry_path) if registry_path else {"entries": []}
    registry_entries = registry_data.get("entries", [])

    packet_mentions = extract_skill_mentions(packet_docs, taxonomy)
    base_mentions = extract_skill_mentions(base_docs, taxonomy)

    # 1. Forbidden rules check
    forbidden_findings = _check_forbidden(packet_docs, base_docs, forbidden_rules)

    # 2. Skill claim verdicts
    claims_report: list[dict[str, Any]] = list(forbidden_findings)

    for canonical in sorted(packet_mentions.keys()):
        items = packet_mentions[canonical]
        positive_items = [it for it in items if not it["disavowed"]]
        disavowed_items = [it for it in items if it["disavowed"]]

        if not positive_items:
            sample = disavowed_items[0]
            claims_report.append(
                {
                    "claim": canonical,
                    "category": sample["category"],
                    "verdict": "DISAVOWED_HONEST_GAP",
                    "document": sample["document"],
                    "matched_text": sample["matched_text"],
                    "excerpt": sample["excerpt"],
                    "evidence": f"Explicit honest-candor disavowal ('{sample['disavowal_trigger']}')",
                    "artifact_id": None,
                }
            )
            continue

        sample = positive_items[0]
        reg_match = _match_registry_for_skill(canonical, tax_by_name[canonical], registry_entries)
        base_pos = [it for it in base_mentions.get(canonical, []) if not it["disavowed"]]

        if reg_match is not None:
            claims_report.append(
                {
                    "claim": canonical,
                    "category": sample["category"],
                    "verdict": "PROVEN_BY_ARTIFACT",
                    "document": sample["document"],
                    "matched_text": sample["matched_text"],
                    "excerpt": sample["excerpt"],
                    "evidence": f"{reg_match['artifact_id']}: {reg_match['matched_claim']}",
                    "artifact_id": reg_match["artifact_id"],
                }
            )
        elif base_pos:
            b = base_pos[0]
            claims_report.append(
                {
                    "claim": canonical,
                    "category": sample["category"],
                    "verdict": "IN_BASE_DOCS",
                    "document": sample["document"],
                    "matched_text": sample["matched_text"],
                    "excerpt": sample["excerpt"],
                    "evidence": f"{b['document']}: \"{b['excerpt'][:140]}\"",
                    "artifact_id": None,
                }
            )
        else:
            claims_report.append(
                {
                    "claim": canonical,
                    "category": sample["category"],
                    "verdict": "UNSUPPORTED",
                    "document": sample["document"],
                    "matched_text": sample["matched_text"],
                    "excerpt": sample["excerpt"],
                    "evidence": "Absent from proof-registry.json and base documents — must remove or soften.",
                    "artifact_id": None,
                }
            )

    # 3. Optional JD comparison (confirming honest omissions)
    jd_label, jd_text = load_jd_text(jd_source)
    jd_skills: list[str] = []
    jd_honestly_omitted: list[str] = []
    if jd_text:
        jd_mentions = extract_skill_mentions([(jd_label or "jd", jd_text)], taxonomy)
        jd_skills = sorted(jd_mentions.keys())
        pos_claimed = {
            c["claim"]
            for c in claims_report
            if c["verdict"] in {"PROVEN_BY_ARTIFACT", "IN_BASE_DOCS", "UNSUPPORTED"}
        }
        jd_honestly_omitted = sorted(s for s in jd_skills if s not in pos_claimed)

    counts = {
        "FORBIDDEN": sum(1 for c in claims_report if c["verdict"] == "FORBIDDEN"),
        "UNSUPPORTED": sum(1 for c in claims_report if c["verdict"] == "UNSUPPORTED"),
        "PROVEN_BY_ARTIFACT": sum(1 for c in claims_report if c["verdict"] == "PROVEN_BY_ARTIFACT"),
        "IN_BASE_DOCS": sum(1 for c in claims_report if c["verdict"] == "IN_BASE_DOCS"),
        "DISAVOWED_HONEST_GAP": sum(
            1 for c in claims_report if c["verdict"] == "DISAVOWED_HONEST_GAP"
        ),
    }
    passed = counts["FORBIDDEN"] == 0 and counts["UNSUPPORTED"] == 0

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "packet_path": str(packet_path),
        "packet_files": [name for name, _ in packet_docs],
        "base_docs_files": [name for name, _ in base_docs],
        "registry_path": str(registry_path),
        "jd_source": jd_label,
        "overall_status": "PASS" if passed else "FAIL",
        "counts": counts,
        "claims": claims_report,
        "jd_skills": jd_skills,
        "jd_honestly_omitted": jd_honestly_omitted,
    }


def render_markdown(report: dict[str, Any]) -> str:
    c = report["counts"]
    lines = [
        "# Packet Claim-Verifier Report (Build A5)",
        "",
        f"- **Generated (UTC):** {report['generated_at_utc']}",
        f"- **Overall Status:** **{report['overall_status']}**",
        f"- **Packet Files:** {', '.join(report['packet_files'])}",
        f"- **Base Docs Loaded:** {', '.join(report['base_docs_files']) if report['base_docs_files'] else 'None'}",
        f"- **JD Source:** {report['jd_source'] or 'Not provided'}",
        "",
        "## Summary Counts",
        "",
        f"| Verdict | Count |",
        f"|---|---:|",
        f"| `FORBIDDEN` | {c['FORBIDDEN']} |",
        f"| `UNSUPPORTED` | {c['UNSUPPORTED']} |",
        f"| `PROVEN_BY_ARTIFACT` | {c['PROVEN_BY_ARTIFACT']} |",
        f"| `IN_BASE_DOCS` | {c['IN_BASE_DOCS']} |",
        f"| `DISAVOWED_HONEST_GAP` | {c['DISAVOWED_HONEST_GAP']} |",
        "",
        "## Claim-by-Claim Verdicts",
        "",
        "| Claim | Verdict | Document | Artifact ID | Evidence / Rationale |",
        "|---|---|---|---|---|",
    ]
    for item in report["claims"]:
        ev = (item.get("evidence") or "").replace("|", "\\|").replace("\n", " ")
        aid = item.get("artifact_id") or "—"
        lines.append(
            f"| {item['claim']} | `{item['verdict']}` | {item['document']} | {aid} | {ev} |"
        )

    if report.get("jd_skills"):
        lines.extend(
            [
                "",
                "## JD Alignment & Honest Omissions",
                "",
                f"- **JD Skills Detected ({len(report['jd_skills'])}):** {', '.join(report['jd_skills'])}",
                f"- **Cleanly Omitted / Disavowed ({len(report['jd_honestly_omitted'])}):** "
                f"{', '.join(report['jd_honestly_omitted']) if report['jd_honestly_omitted'] else 'None'}",
            ]
        )

    lines.append("")
    lines.append(
        "*Read-only verification by Tosson Services LLC dba Tosson Environmental Analytics — nothing is submitted or sent.*"
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify job-application packet claims against proof registry and base docs.")
    parser.add_argument("--packet", required=True, help="Path to packet file or directory (.docx/.txt/.md)")
    parser.add_argument("--jd", default=None, help="Optional JD file path or URL")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH), help="Path to proof-registry.json")
    parser.add_argument("--base-docs", default=None, help="Optional path to base resume/cover-letter file or directory")
    parser.add_argument("--out-md", type=Path, default=None, help="Optional Markdown output path")
    parser.add_argument("--out-json", type=Path, default=None, help="Optional JSON output path")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any FORBIDDEN or UNSUPPORTED verdict exists")
    args = parser.parse_args(argv)

    report = verify_packet(
        packet_path=args.packet,
        registry_path=args.registry,
        base_docs_path=args.base_docs,
        jd_source=args.jd,
    )
    md = render_markdown(report)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(md, encoding="utf-8")
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(md)
    if args.strict and report["overall_status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
