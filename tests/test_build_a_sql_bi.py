"""Build A4 SQL + Snowflake (dialect-only) + Power BI DAX/Model + HTML Dashboard tests.

Runs 100% offline with NO fixtures/ directory using synthetic DuckDB build.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = WORKSPACE_ROOT / "portfolio-factory"
SYNTH_DIR = WORKSPACE_ROOT / "tests" / "fixtures_synthetic" / "build_a"
DBT_DIR = REPO_ROOT / "pfas_warehouse"


def _resolve_dbt_bin() -> str:
    candidates = [
        os.environ.get("PFAS_DBT_BIN"),
        str(WORKSPACE_ROOT / ".venv" / "bin" / "dbt"),
        str(Path(sys.executable).parent / "dbt"),
        shutil.which("dbt"),
    ]
    for cand in candidates:
        if cand and Path(cand).exists():
            return str(cand)
    return "dbt"


DBT_BIN = _resolve_dbt_bin()

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.build_dashboard import build_dashboard
from ingest.ingest_ucmr5 import run_ingest
from sql.run_sql_pack import run_sql_pack


def test_sql_pack_and_dashboard_on_synthetic_db(tmp_path: Path) -> None:
    db_path = tmp_path / "sql_bi_test.duckdb"
    run_ingest(
        input_file=SYNTH_DIR / "ucmr5_mini.tsv",
        county_file=SYNTH_DIR / "sdwis_counties_mini.csv",
        db_path=db_path,
        skip_registry=True,
    )
    env = os.environ.copy()
    env["PFAS_DUCKDB_PATH"] = str(db_path)
    subprocess.run(
        [
            DBT_BIN, "build",
            "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR),
            "--target-path", str(tmp_path / "dbt_target"),
            "--log-path", str(tmp_path / "dbt_logs"),
        ],
        check=True, env=env, capture_output=True, text=True,
    )

    # All 10 advanced SQL patterns execute cleanly and return non-empty results
    sql_res = run_sql_pack(db_path=db_path, skip_registry=True)
    assert sql_res["queries_executed"] == 10
    assert sql_res["all_passed"] is True
    for item in sql_res["results"]:
        assert item["row_count"] >= 1, f"{item['file']} returned 0 rows"

    # Build self-contained HTML dashboard from synthetic DuckDB marts
    out_html = tmp_path / "index.html"
    dash_res = build_dashboard(db_path=db_path, out_html=out_html, skip_registry=True)
    assert out_html.exists()
    assert dash_res["counties"] == 3
    assert dash_res["systems"] == 3
    html_txt = out_html.read_text(encoding="utf-8")
    assert "Tosson Services LLC dba Tosson Environmental Analytics" in html_txt
    assert "proposed / not final" in html_txt.lower()
    assert "https://www.epa.gov/sdwa/proposed-pfas-rescission-rule" in html_txt
    assert ("violat" + "ion") not in html_txt.lower()
    # Zero external CDN script/stylesheet links
    assert "<script src=" not in html_txt.lower()
    assert "<link rel=\"stylesheet\" href=\"http" not in html_txt.lower()


def test_sql_headers_snowflake_dialect_labels_and_powerbi_specs() -> None:
    banned = "violat" + "ion"

    # A4a: Every SQL file names JD KEYWORDS EVIDENCED and avoids banned word
    sql_files = sorted((REPO_ROOT / "sql").glob("[0-9][0-9]_*.sql"))
    assert len(sql_files) == 10
    for f in sql_files:
        txt = f.read_text(encoding="utf-8")
        assert "JD KEYWORDS EVIDENCED:" in txt
        assert banned not in txt.lower()

    # A4b: Every Snowflake SQL file and README explicitly labelled dialect-only (unexecuted)
    sf_files = sorted((REPO_ROOT / "snowflake").glob("*.sql"))
    assert len(sf_files) == 4
    for f in sf_files + [REPO_ROOT / "snowflake" / "README.md"]:
        txt = f.read_text(encoding="utf-8")
        assert "dialect-only" in txt.lower()
        assert "not executed against a snowflake account" in txt.lower()
        assert banned not in txt.lower()

    # A4c: Power BI DAX library + semantic model spec + model_spec.json
    dax_txt = (REPO_ROOT / "powerbi" / "measures.dax").read_text(encoding="utf-8")
    assert "[Detection Rate %]" in dax_txt
    assert "[System-Event Hazard Index (Max)]" in dax_txt
    assert "[Detection Rate YoY Delta (pp)]" in dax_txt
    assert "[County Rank by Samples Above Benchmark]" in dax_txt
    assert "no .pbix" in dax_txt.lower()
    assert banned not in dax_txt.lower()

    spec_md = (REPO_ROOT / "powerbi" / "semantic_model.md").read_text(encoding="utf-8")
    assert "proposed / not final" in spec_md.lower()
    assert "Tosson Services LLC dba Tosson Environmental Analytics" in spec_md
    assert banned not in spec_md.lower()

    spec_json = json.loads((REPO_ROOT / "powerbi" / "model_spec.json").read_text(encoding="utf-8"))
    assert spec_json["pbix_included"] is False
    assert len(spec_json["tables"]) == 5
    assert len(spec_json["relationships"]) == 4

    # A4d: Committed dashboard HTML built from live warehouse exists and is clean
    live_html = (REPO_ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert "North Carolina EPA UCMR 5 PFAS Screening Explorer" in live_html
    assert "Tosson Services LLC dba Tosson Environmental Analytics" in live_html
    assert banned not in live_html.lower()
