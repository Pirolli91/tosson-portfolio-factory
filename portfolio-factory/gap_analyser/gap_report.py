"""Build A6: Ranked JD Gap Analyser.

Reads captured official JD snapshots (from capture_seed_jds.py) or local JD files,
extracts required/mentioned skills via verifier/skill_taxonomy.yaml, diffs them
against proof-registry.json and optional base documents, and scores ranked gaps
using `gap_score = sum(target_role_weight for each OPEN JD requiring the skill)`
(equivalently frequency * weighted role priority).

Writes `portfolio-factory/reports/jd_gap_report.md` and `.json`, and upserts
`a6-jd-gap-analyser` in `proof-registry.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GAP_DIR = Path(__file__).resolve().parent
REPO_ROOT = GAP_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.proof_registry import DEFAULT_REGISTRY_PATH, load_registry, upsert_entry
from verifier.verify_packet import (
    DEFAULT_TAXONOMY_PATH,
    _match_registry_for_skill,
    extract_skill_mentions,
    load_documents,
    load_taxonomy,
)

DEFAULT_SNAPSHOTS_DIR = GAP_DIR / "snapshots"
DEFAULT_OUT_MD = REPO_ROOT / "reports" / "jd_gap_report.md"
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "jd_gap_report.json"


def _load_snapshots(snapshots_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for p in sorted(Path(snapshots_dir).glob("*.json")):
        if p.name == "capture_manifest.json":
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        if "jd_id" in data:
            records.append(data)
    return records


def build_gap_report(
    *,
    snapshots_dir: Path = DEFAULT_SNAPSHOTS_DIR,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    base_docs_path: Path | None = None,
    out_md: Path = DEFAULT_OUT_MD,
    out_json: Path = DEFAULT_OUT_JSON,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
    workspace_root: Path = WORKSPACE_ROOT,
    skip_registry: bool = False,
) -> dict[str, Any]:
    snapshots = _load_snapshots(Path(snapshots_dir))
    if not snapshots:
        raise FileNotFoundError(f"No JD snapshots found in {snapshots_dir}")

    taxonomy = load_taxonomy(taxonomy_path)
    tax_by_name = {t["canonical"]: t for t in taxonomy}

    registry_data = load_registry(registry_path) if registry_path else {"entries": []}
    registry_entries = registry_data.get("entries", [])
    base_docs = load_documents(base_docs_path)
    base_mentions = extract_skill_mentions(base_docs, taxonomy)

    skill_demand: dict[str, dict[str, Any]] = {}
    jd_summaries: list[dict[str, Any]] = []

    for snap in snapshots:
        status = snap.get("status", "UNKNOWN")
        text = snap.get("text", "") or ""
        weight = float(snap.get("target_role_weight", 1.0))
        extracted: list[str] = []

        if status == "OPEN" and text.strip():
            mentions = extract_skill_mentions([(snap["jd_id"], text)], taxonomy)
            extracted = sorted(mentions.keys())
            for canonical in extracted:
                bucket = skill_demand.setdefault(
                    canonical,
                    {
                        "skill": canonical,
                        "category": tax_by_name[canonical]["category"],
                        "frequency": 0,
                        "weighted_score": 0.0,
                        "jds": [],
                    },
                )
                bucket["frequency"] += 1
                bucket["weighted_score"] = round(bucket["weighted_score"] + weight, 3)
                bucket["jds"].append(snap["jd_id"])

        jd_summaries.append(
            {
                "jd_id": snap["jd_id"],
                "company": snap.get("company", ""),
                "role_title": snap.get("role_title", ""),
                "req_id": snap.get("req_id", ""),
                "target_role_weight": weight,
                "official_url": snap.get("official_url", ""),
                "canonical_url": snap.get("canonical_url", snap.get("official_url", "")),
                "http_status": snap.get("http_status", 0),
                "captured_at_utc": snap.get("captured_at_utc", ""),
                "status": status,
                "status_reason": snap.get("status_reason", ""),
                "skills_extracted": extracted,
            }
        )

    ranked_skills: list[dict[str, Any]] = []
    for canonical, bucket in skill_demand.items():
        reg_match = _match_registry_for_skill(canonical, tax_by_name[canonical], registry_entries)
        base_pos = [it for it in base_mentions.get(canonical, []) if not it["disavowed"]]

        if reg_match is not None:
            coverage = "COVERED_BY_ARTIFACT"
            evidence = f"{reg_match['artifact_id']}: {reg_match['matched_claim']}"
            gap_score = 0.0
        elif base_pos:
            coverage = "COVERED_BY_BASE_DOCS"
            evidence = f"{base_pos[0]['document']}"
            gap_score = 0.0
        else:
            coverage = "TRUE_GAP"
            evidence = "Not present in proof-registry.json or base documents"
            gap_score = bucket["weighted_score"]

        ranked_skills.append(
            {
                "skill": canonical,
                "category": bucket["category"],
                "frequency": bucket["frequency"],
                "demand_score": bucket["weighted_score"],
                "gap_score": gap_score,
                "coverage_status": coverage,
                "evidence": evidence,
                "jds": bucket["jds"],
            }
        )

    ranked_skills.sort(key=lambda x: (-x["gap_score"], -x["demand_score"], x["skill"]))
    true_gaps = [s for s in ranked_skills if s["coverage_status"] == "TRUE_GAP"]
    covered_artifacts = [s for s in ranked_skills if s["coverage_status"] == "COVERED_BY_ARTIFACT"]
    covered_base = [s for s in ranked_skills if s["coverage_status"] == "COVERED_BY_BASE_DOCS"]

    gen_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "generated_at_utc": gen_ts,
        "legal_entity": "Tosson Services LLC dba Tosson Environmental Analytics",
        "jds_total": len(jd_summaries),
        "jds_open": sum(1 for j in jd_summaries if j["status"] == "OPEN"),
        "jds_closed": sum(1 for j in jd_summaries if j["status"] == "CLOSED"),
        "jds_unfetchable_bot_gate": sum(
            1 for j in jd_summaries if j["status"] == "UNFETCHABLE_BOT_GATE"
        ),
        "seed_jds": jd_summaries,
        "ranked_skills": ranked_skills,
        "summary": {
            "total_unique_jd_skills": len(ranked_skills),
            "covered_by_artifact": len(covered_artifacts),
            "covered_by_base_docs": len(covered_base),
            "true_gaps": len(true_gaps),
        },
    }

    md_lines = [
        "# JD Skill Gap Analysis Report (Build A6)",
        "",
        f"- **Generated (UTC):** {gen_ts}",
        f"- **Owner / Legal Entity:** Tosson Services LLC dba Tosson Environmental Analytics",
        f"- **Seed JDs Evaluated:** {report['jds_total']} "
        f"(`OPEN={report['jds_open']}`, `CLOSED={report['jds_closed']}`, `UNFETCHABLE_BOT_GATE={report['jds_unfetchable_bot_gate']}`)",
        "",
        "## Live Seed JD Capture Status (Official Employer Career Pages Only)",
        "",
        "| JD ID | Company | Role | Req ID | Weight | HTTP | Status | Captured (UTC) | Official URL |",
        "|---|---|---|---|---:|---:|---|---|---|",
    ]
    for j in jd_summaries:
        md_lines.append(
            f"| `{j['jd_id']}` | {j['company']} | {j['role_title']} | `{j['req_id']}` | "
            f"{j['target_role_weight']:.1f} | {j['http_status']} | `{j['status']}` | "
            f"{j['captured_at_utc']} | {j['official_url']} |"
        )

    md_lines.extend(
        [
            "",
            "*Standing rule note: Postings gated by Cloudflare/Workday anti-bot challenges or rate limits are recorded honestly as `UNFETCHABLE_BOT_GATE` (never bypassed and never reconstructed from memory or aggregators). Closed postings are recorded as `CLOSED` with UTC capture date.*",
            "",
            "## Ranked Skills & Remaining Gaps (`gap_score = frequency × target_role_weight`)",
            "",
            "| Rank | Skill | Category | Freq | Demand Score | Gap Score | Coverage | Evidence | JDs |",
            "|---:|---|---|---:|---:|---:|---|---|---|",
        ]
    )
    if ranked_skills:
        for idx, item in enumerate(ranked_skills, start=1):
            ev = item["evidence"].replace("|", "\\|")
            md_lines.append(
                f"| {idx} | {item['skill']} | {item['category']} | {item['frequency']} | "
                f"{item['demand_score']:.2f} | {item['gap_score']:.2f} | `{item['coverage_status']}` | "
                f"{ev} | {', '.join(item['jds'])} |"
            )
    else:
        md_lines.append("| — | *(No OPEN JDs yielded extractable taxonomy skills)* | — | 0 | 0.00 | 0.00 | — | — | — |")

    md_lines.append("")
    out_md = Path(out_md)
    out_json = Path(out_json)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if not skip_registry and registry_path is not None:
        source_urls = [j["official_url"] for j in jd_summaries if j.get("official_url")]
        upsert_entry(
            {
                "artifact_id": "a6-jd-gap-analyser",
                "kind": "report",
                "title": "Live Official-Page JD Capture & Ranked Skill Gap Report",
                "repo_path": "portfolio-factory/reports/jd_gap_report.md",
                "evidence": {
                    "command": ".venv/bin/python portfolio-factory/gap_analyser/capture_seed_jds.py && .venv/bin/python portfolio-factory/gap_analyser/gap_report.py",
                    "result": (
                        f"PASS (jds_total={report['jds_total']}, OPEN={report['jds_open']}, "
                        f"CLOSED={report['jds_closed']}, UNFETCHABLE_BOT_GATE={report['jds_unfetchable_bot_gate']}, "
                        f"skills_evaluated={report['summary']['total_unique_jd_skills']}, "
                        f"true_gaps={report['summary']['true_gaps']})"
                    ),
                    "timestamp": gen_ts,
                    "metrics": report["summary"],
                },
                "supports_claims": [
                    "Built automated JD gap analyser capturing live official career postings and scoring skill gaps against runnable portfolio proof",
                    "Python",
                ],
                "source_urls": source_urls,
            },
            registry_path=registry_path,
            workspace_root=workspace_root,
            check_path=True,
        )

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate ranked JD skill gap report.")
    parser.add_argument("--snapshots-dir", type=Path, default=DEFAULT_SNAPSHOTS_DIR)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--base-docs", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--skip-registry", action="store_true")
    args = parser.parse_args(argv)

    rep = build_gap_report(
        snapshots_dir=args.snapshots_dir,
        registry_path=args.registry,
        base_docs_path=args.base_docs,
        out_md=args.out_md,
        out_json=args.out_json,
        skip_registry=args.skip_registry,
    )
    print(json.dumps(rep["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
