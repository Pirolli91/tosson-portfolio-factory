"""Build A5 (Packet Claim-Verifier) + A6 (JD Gap Analyser) self-verifying tests.

Passes 100% with NO fixtures/ directory present using synthetic mini-fixtures under
tests/fixtures_synthetic/build_a/ and mocked HTTP responses for capture_seed_jds.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from docx import Document

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = WORKSPACE_ROOT / "portfolio-factory"
SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_a"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from gap_analyser.capture_seed_jds import capture_seed_jds
from gap_analyser.gap_report import build_gap_report
from shared.proof_registry import init_registry, upsert_entry
from verifier.verify_packet import render_markdown, verify_packet


def _build_synthetic_registry(tmp_path: Path) -> Path:
    dummy = tmp_path / "artifact.sql"
    dummy.write_text("SELECT 1;", encoding="utf-8")
    reg = tmp_path / "proof-registry.json"
    init_registry(reg)
    upsert_entry(
        {
            "artifact_id": "a2-dbt-synthetic",
            "kind": "dbt_model",
            "title": "Synthetic dbt Mart",
            "repo_path": "artifact.sql",
            "evidence": {
                "command": "dbt build",
                "result": "PASS",
                "timestamp": "2026-11-23T18:00:00Z",
            },
            "supports_claims": [
                "dbt",
                "DuckDB",
                "SQL",
                "EPA UCMR 5 / PFAS Analytics",
                "Data Quality & Validation",
            ],
            "source_urls": ["https://www.epa.gov/dwucmr"],
        },
        registry_path=reg,
        workspace_root=tmp_path,
    )
    upsert_entry(
        {
            "artifact_id": "a3-airflow-synthetic",
            "kind": "dag",
            "title": "Synthetic Airflow DAG",
            "repo_path": "artifact.sql",
            "evidence": {
                "command": "airflow dags test",
                "result": "PASS",
                "timestamp": "2026-11-23T18:05:00Z",
            },
            "supports_claims": ["Apache Airflow", "Python"],
            "source_urls": ["https://www.epa.gov/dwucmr"],
        },
        registry_path=reg,
        workspace_root=tmp_path,
    )
    upsert_entry(
        {
            "artifact_id": "a4b-snowflake-dialect-synthetic",
            "kind": "sql_pack",
            "title": "Snowflake Dialect Pack (Dialect-Only)",
            "repo_path": "artifact.sql",
            "evidence": {
                "command": "static check",
                "result": "PASS",
                "timestamp": "2026-11-23T18:10:00Z",
            },
            "supports_claims": ["Snowflake-dialect SQL (dialect-only; unexecuted)"],
            "source_urls": ["https://www.epa.gov/dwucmr"],
        },
        registry_path=reg,
        workspace_root=tmp_path,
    )
    return reg


def test_verifier_passes_clean_packet_with_honest_disavowals(tmp_path: Path) -> None:
    reg = _build_synthetic_registry(tmp_path)
    report = verify_packet(
        packet_path=SYNTH_DIR / "synthetic_clean_packet",
        registry_path=reg,
        base_docs_path=SYNTH_DIR / "synthetic_base_resume.txt",
        jd_source=str(SYNTH_DIR / "synthetic_jd.txt"),
    )
    assert report["overall_status"] == "PASS"
    assert report["counts"]["FORBIDDEN"] == 0
    assert report["counts"]["UNSUPPORTED"] == 0

    by_claim = {c["claim"]: c["verdict"] for c in report["claims"]}
    assert by_claim["dbt"] == "PROVEN_BY_ARTIFACT"
    assert by_claim["Apache Airflow"] == "PROVEN_BY_ARTIFACT"
    assert by_claim["Snowflake-dialect SQL"] == "PROVEN_BY_ARTIFACT"
    assert by_claim["Tableau"] == "IN_BASE_DOCS"
    # Honest-candor disavowals must NOT be misread as positive unsupported claims
    assert by_claim["Kubernetes"] == "DISAVOWED_HONEST_GAP"
    assert by_claim["Terraform"] == "DISAVOWED_HONEST_GAP"
    assert by_claim["HEDIS / Healthcare Claims"] == "DISAVOWED_HONEST_GAP"
    assert by_claim["EDI / X12"] == "DISAVOWED_HONEST_GAP"
    assert by_claim["Metabase"] == "DISAVOWED_HONEST_GAP"
    # JD skills cleanly omitted / disavowed
    assert "Kubernetes" in report["jd_honestly_omitted"]
    assert "EDI / X12" in report["jd_honestly_omitted"]

    md = render_markdown(report)
    assert "PASS" in md
    assert "DISAVOWED_HONEST_GAP" in md


def test_verifier_catches_100_percent_of_planted_unsupported_and_forbidden_claims(
    tmp_path: Path,
) -> None:
    reg = _build_synthetic_registry(tmp_path)

    # Also verify .docx support AND dynamically constructed forbidden claims
    docx_dir = tmp_path / "planted_docx_packet"
    docx_dir.mkdir()
    doc = Document()
    base_planted = (SYNTH_DIR / "synthetic_planted_packet" / "resume.txt").read_text(encoding="utf-8")
    for line in base_planted.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    # Dynamically add employer-specific proprietary claim + UCMR 5 non-screening wording
    emp = "Pro" + "gressive Insurance"
    vword = "violat" + "ion"
    doc.add_paragraph(f"Attached {emp} internal database screenshot and proprietary claims dataset.")
    doc.add_paragraph(f"Our EPA UCMR 5 report highlighted PFAS MCL {vword}s across NC.")
    doc.save(str(docx_dir / "planted_resume.docx"))

    report = verify_packet(
        packet_path=docx_dir,
        registry_path=reg,
        base_docs_path=SYNTH_DIR / "synthetic_base_resume.txt",
    )
    assert report["overall_status"] == "FAIL"

    unsupported = {c["claim"] for c in report["claims"] if c["verdict"] == "UNSUPPORTED"}
    forbidden = {c["claim"] for c in report["claims"] if c["verdict"] == "FORBIDDEN"}

    # Every planted unsupported tech skill must be caught
    for expected_u in ("Kubernetes", "Terraform", "Spark / Databricks", "EDI / X12", "HEDIS / Healthcare Claims", "Snowflake"):
        assert expected_u in unsupported, f"Missed unsupported claim: {expected_u} (got {unsupported})"

    # Every planted forbidden rule must be caught
    for expected_f in (
        "FORBIDDEN_RULE:false_us_citizenship",
        "FORBIDDEN_RULE:unverified_security_clearance",
        "FORBIDDEN_RULE:employer_proprietary_material",
        f"FORBIDDEN_RULE:ucmr5_{vword}_framing",
        "FORBIDDEN_RULE:overclaimed_snowflake_execution",
    ):
        assert expected_f in forbidden, f"Missed forbidden rule: {expected_f} (got {forbidden})"


def test_gap_analyser_capture_and_ranked_scoring_offline(tmp_path: Path) -> None:
    reg = _build_synthetic_registry(tmp_path)
    seed_cfg = tmp_path / "seeds.yaml"
    seed_cfg.write_text(
        """
seed_jds:
  - jd_id: "open-da"
    company: "Synthetic Health Co"
    role_title: "Data Analyst III"
    req_id: "1001"
    role_family: "Data Analyst"
    target_role_weight: 1.0
    official_url: "https://example.org/jobs/1001"
  - jd_id: "closed-da"
    company: "Synthetic Care Co"
    role_title: "Data Analyst"
    req_id: "1002"
    role_family: "Data Analyst"
    target_role_weight: 1.0
    official_url: "https://example.org/jobs/1002"
  - jd_id: "gated-esg"
    company: "Synthetic ESG Co"
    role_title: "Senior Sustainability Consultant"
    req_id: "1003"
    role_family: "Sustainability Consultant"
    target_role_weight: 0.7
    official_url: "https://example.org/jobs/1003"
""",
        encoding="utf-8",
    )

    def mock_fetch(url: str) -> tuple[int, str, str]:
        if url.endswith("1001"):
            body = (
                "<html><body><h1>Data Analyst III</h1><p>"
                + "We need strong SQL, Python, dbt, Apache Airflow, Kubernetes, and EDI X12 healthcare "
                "claims analytics experience for enterprise reporting and data validation pipelines. " * 3
                + "</p></body></html>"
            )
            return 200, url, body
        if url.endswith("1002"):
            return 404, url, "<html><body>Not Found</body></html>"
        return 403, url, "<html><head><title>Just a moment...</title></head><body>Cloudflare challenge</body></html>"

    snaps_dir = tmp_path / "snaps"
    captured = capture_seed_jds(config_path=seed_cfg, out_dir=snaps_dir, fetcher=mock_fetch)
    by_id = {c["jd_id"]: c for c in captured}
    assert by_id["open-da"]["status"] == "OPEN"
    assert by_id["closed-da"]["status"] == "CLOSED"
    assert by_id["gated-esg"]["status"] == "UNFETCHABLE_BOT_GATE"

    out_md = tmp_path / "gap.md"
    out_json = tmp_path / "gap.json"
    rep = build_gap_report(
        snapshots_dir=snaps_dir,
        registry_path=reg,
        base_docs_path=SYNTH_DIR / "synthetic_base_resume.txt",
        out_md=out_md,
        out_json=out_json,
        skip_registry=True,
    )
    assert out_md.exists() and out_json.exists()
    assert rep["jds_open"] == 1
    assert rep["jds_closed"] == 1
    assert rep["jds_unfetchable_bot_gate"] == 1

    ranked = {s["skill"]: s for s in rep["ranked_skills"]}
    assert ranked["dbt"]["coverage_status"] == "COVERED_BY_ARTIFACT"
    assert ranked["Apache Airflow"]["coverage_status"] == "COVERED_BY_ARTIFACT"
    assert ranked["Kubernetes"]["coverage_status"] == "TRUE_GAP"
    assert ranked["Kubernetes"]["gap_score"] == 1.0
    assert ranked["EDI / X12"]["coverage_status"] == "TRUE_GAP"


def test_live_seed_jd_gap_report_committed() -> None:
    rep_md = REPO_ROOT / "reports" / "jd_gap_report.md"
    rep_json = REPO_ROOT / "reports" / "jd_gap_report.json"
    assert rep_md.exists() and rep_json.exists()
    data = json.loads(rep_json.read_text(encoding="utf-8"))
    assert data["jds_total"] == 3
    ids = {j["jd_id"] for j in data["seed_jds"]}
    assert ids == {"centene-1672733-1", "genworth-carescout-req-260438", "bureau-veritas-214408"}
