"""Build A4d: Self-contained Interactive HTML Dashboard Generator for NC EPA UCMR 5 PFAS Screening.

Reads verified dbt marts from DuckDB (read-only) and renders a single self-contained
HTML file with zero external CDN dependencies: interactive county & analyte filters,
KPI summary cards, inline SVG bar charts, sortable county & water-system tables,
UCMR 5 screening-only disclaimer, D5 regulatory-status footnote (proposed / not final),
and Tosson Services LLC dba Tosson Environmental Analytics attribution.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

DASH_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASH_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from shared.proof_registry import DEFAULT_REGISTRY_PATH, upsert_entry

DEFAULT_DB_PATH = REPO_ROOT / "warehouse" / "pfas_ucmr5.duckdb"
DEFAULT_OUT_HTML = DASH_DIR / "index.html"


def _fetch_dicts(con: duckdb.DuckDBPyConnection, query: str) -> list[dict[str, Any]]:
    rel = con.execute(query)
    cols = [d[0] for d in rel.description]
    out: list[dict[str, Any]] = []
    for row in rel.fetchall():
        item: dict[str, Any] = {}
        for k, v in zip(cols, row):
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            else:
                item[k] = v
        out.append(item)
    return out


def build_dashboard(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    out_html: Path = DEFAULT_OUT_HTML,
    registry_path: Path | None = DEFAULT_REGISTRY_PATH,
    workspace_root: Path = WORKSPACE_ROOT,
    skip_registry: bool = False,
) -> dict[str, Any]:
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB warehouse not found: {db_path}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        audit_rows = _fetch_dicts(con, "SELECT * FROM raw_ucmr5.ingest_audit LIMIT 1")
        counties = _fetch_dicts(
            con,
            """
            SELECT
                county_name, systems_monitored, total_samples, pfas_samples,
                pfas_detected_samples, pfas_detection_rate_pct,
                samples_above_mcl_benchmark, systems_above_mcl_benchmark,
                systems_above_hi_benchmark, systems_above_any_2024_benchmark,
                share_systems_above_benchmark_pct, max_benchmark_ratio,
                max_detected_pfas_ppt, max_hazard_index_score,
                primary_exceeding_analyte, screening_summary_label
            FROM main_marts.mart_county_scorecard
            ORDER BY samples_above_mcl_benchmark DESC, systems_above_any_2024_benchmark DESC, county_name ASC
            """,
        )
        analytes = _fetch_dicts(
            con,
            """
            SELECT
                contaminant, analyte_group, mcl_benchmark_ppt, hbwc_ppt,
                in_hazard_index, total_samples, systems_tested, detected_samples,
                detection_rate_pct, p50_detected_ppt, p90_detected_ppt,
                max_detected_ppt, samples_above_mcl_benchmark, systems_above_mcl_benchmark
            FROM main_marts.mart_analyte_summary
            ORDER BY samples_above_mcl_benchmark DESC, detected_samples DESC, contaminant ASC
            """,
        )
        systems = _fetch_dicts(
            con,
            """
            SELECT
                pwsid, pws_name, county_name, size_category,
                total_samples, pfas_detected_samples, samples_above_mcl_benchmark,
                max_pfoa_ppt, max_pfos_ppt, max_pfhxs_ppt, max_pfna_ppt,
                max_hfpo_da_ppt, max_pfbs_ppt, max_benchmark_ratio,
                max_hazard_index_score, screening_status
            FROM main_marts.mart_system_screening
            ORDER BY samples_above_mcl_benchmark DESC, max_benchmark_ratio DESC NULLS LAST, pwsid ASC
            """,
        )
    finally:
        con.close()

    audit = audit_rows[0] if audit_rows else {}
    total_samples = sum(int(c["total_samples"]) for c in counties)
    total_pfas_det = sum(int(c["pfas_detected_samples"]) for c in counties)
    total_above_mcl = sum(int(c["samples_above_mcl_benchmark"]) for c in counties)
    total_sys_above = sum(int(c["systems_above_any_2024_benchmark"]) for c in counties)
    total_counties = len(counties)
    total_systems = len(systems)

    generated_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "generated_at_utc": generated_ts,
        "kpis": {
            "total_samples": total_samples,
            "total_counties": total_counties,
            "total_systems": total_systems,
            "total_pfas_detections": total_pfas_det,
            "total_samples_above_mcl_benchmark": total_above_mcl,
            "total_systems_above_any_2024_benchmark": total_sys_above,
            "source_file_sha256": audit.get("source_file_sha256", ""),
        },
        "counties": counties,
        "analytes": analytes,
        "systems": systems,
    }
    safe_json = json.dumps(payload).replace("</", "<\\/")

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>North Carolina EPA UCMR 5 PFAS Screening Explorer — Tosson Environmental Analytics</title>
<style>
  :root {{
    --bg: #0f172a;
    --panel: #1e293b;
    --panel-alt: #162033;
    --border: #334155;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --warn: #f59e0b;
    --alert: #fb7185;
    --ok: #34d399;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}
  header {{
    background: linear-gradient(135deg, #0b1325, #172554);
    border-bottom: 1px solid var(--border);
    padding: 1.5rem 2rem;
  }}
  header h1 {{ margin: 0 0 0.35rem 0; font-size: 1.55rem; color: #f8fafc; }}
  header p {{ margin: 0; color: var(--muted); font-size: 0.92rem; }}
  .banner {{
    background: #172554;
    border-left: 4px solid var(--accent);
    padding: 0.85rem 1.2rem;
    margin: 1rem 2rem 0 2rem;
    border-radius: 6px;
    font-size: 0.88rem;
  }}
  main {{ padding: 1.25rem 2rem 2.5rem 2rem; max-width: 1440px; margin: 0 auto; }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
    gap: 0.9rem;
    margin-bottom: 1.5rem;
  }}
  .kpi-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.1rem;
  }}
  .kpi-label {{ font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }}
  .kpi-value {{ font-size: 1.65rem; font-weight: 700; margin-top: 0.25rem; color: #f8fafc; }}
  .kpi-sub {{ font-size: 0.78rem; color: var(--accent); margin-top: 0.15rem; }}
  .controls {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 0.9rem 1rem;
    border-radius: 8px;
    align-items: center;
  }}
  .controls label {{ font-size: 0.82rem; color: var(--muted); margin-right: 0.3rem; }}
  .controls input, .controls select {{
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 0.42rem 0.65rem;
    font-size: 0.88rem;
  }}
  .charts-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
    gap: 1.25rem;
    margin-bottom: 1.5rem;
  }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 1.25rem;
  }}
  .card h2 {{ margin: 0 0 0.75rem 0; font-size: 1.08rem; color: #f8fafc; }}
  .table-wrap {{ overflow-x: auto; max-height: 440px; overflow-y: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; }}
  th, td {{ padding: 0.52rem 0.65rem; border-bottom: 1px solid var(--border); text-align: left; }}
  th {{
    background: var(--panel-alt);
    position: sticky;
    top: 0;
    cursor: pointer;
    user-select: none;
    color: #cbd5e1;
    white-space: nowrap;
  }}
  th:hover {{ color: var(--accent); }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr:hover td {{ background: rgba(56, 189, 248, 0.06); }}
  .badge {{
    display: inline-block;
    padding: 0.14rem 0.5rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
  }}
  .badge-alert {{ background: rgba(251, 113, 133, 0.16); color: var(--alert); border: 1px solid rgba(251, 113, 133, 0.4); }}
  .badge-warn {{ background: rgba(245, 158, 11, 0.16); color: var(--warn); border: 1px solid rgba(245, 158, 11, 0.4); }}
  .badge-ok {{ background: rgba(52, 211, 153, 0.14); color: var(--ok); border: 1px solid rgba(52, 211, 153, 0.35); }}
  footer {{
    border-top: 1px solid var(--border);
    padding: 1.25rem 2rem 2rem 2rem;
    color: var(--muted);
    font-size: 0.82rem;
    background: #0b1325;
  }}
  footer a {{ color: var(--accent); }}
</style>
</head>
<body>
<header>
  <h1>North Carolina EPA UCMR 5 PFAS Screening Explorer</h1>
  <p>Built from public-domain U.S. EPA UCMR 5 &amp; SDWIS datasets via dbt-core + DuckDB &bull; Generated {html.escape(generated_ts)} &bull; Tosson Services LLC dba Tosson Environmental Analytics</p>
</header>

<div class="banner">
  <strong>UCMR 5 Screening-Only Framing:</strong> All counts and ratios compare public EPA UCMR 5 unregulated contaminant occurrence data against EPA's six 2024 PFAS drinking-water screening benchmarks (PFOA 4 ppt, PFOS 4 ppt, PFHxS 10 ppt, PFNA 10 ppt, HFPO-DA 10 ppt, and Hazard Index 1.0 using HBWCs HFPO-DA=10, PFNA=10, PFHxS=10, PFBS=2,000 ppt) strictly for informational occurrence screening — never regulatory compliance determinations.
</div>

<main>
  <section class="kpi-grid" id="kpi-grid"></section>

  <section class="controls">
    <div>
      <label for="countySearch">County / System Search:</label>
      <input id="countySearch" type="text" placeholder="e.g., Cumberland, Wake, Nash..." />
    </div>
    <div>
      <label for="statusFilter">County Screening Status:</label>
      <select id="statusFilter">
        <option value="ALL">All Screening Statuses</option>
        <option value="Above 2024 Screening Benchmark Observed">Above 2024 Screening Benchmark Observed</option>
        <option value="PFAS Detected Below 2024 Screening Benchmarks">PFAS Detected Below 2024 Screening Benchmarks</option>
        <option value="No PFAS Detections (>= MRL)">No PFAS Detections (&gt;= MRL)</option>
      </select>
    </div>
    <div>
      <label for="analyteFilter">Primary Exceeding Analyte:</label>
      <select id="analyteFilter">
        <option value="ALL">All Analytes</option>
      </select>
    </div>
  </section>

  <section class="charts-grid">
    <div class="card">
      <h2>Top 12 NC Counties by Samples Above 2024 MCL Screening Benchmarks</h2>
      <div id="countyChart"></div>
    </div>
    <div class="card">
      <h2>Top 10 Monitored PFAS Analytes by Quantified Detections (&gt;= MRL)</h2>
      <div id="analyteChart"></div>
    </div>
  </section>

  <section class="card">
    <h2>NC County Screening Scorecard (<span id="countyCountLabel">0</span> counties shown &mdash; click headers to sort)</h2>
    <div class="table-wrap">
      <table id="countyTable">
        <thead>
          <tr>
            <th data-col="county_name">County</th>
            <th class="num" data-col="systems_monitored">Systems</th>
            <th class="num" data-col="total_samples">Samples</th>
            <th class="num" data-col="pfas_detected_samples">PFAS Detections</th>
            <th class="num" data-col="samples_above_mcl_benchmark">Above 2024 MCL Benchmark</th>
            <th class="num" data-col="systems_above_any_2024_benchmark">Systems Above Benchmark</th>
            <th class="num" data-col="max_benchmark_ratio">Max Benchmark Ratio (x)</th>
            <th class="num" data-col="max_hazard_index_score">Max Hazard Index</th>
            <th data-col="primary_exceeding_analyte">Primary Analyte</th>
            <th data-col="screening_summary_label">Screening Status</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <h2>NC Public Water System Screening Detail (<span id="systemCountLabel">0</span> systems shown &mdash; click headers to sort)</h2>
    <div class="table-wrap">
      <table id="systemTable">
        <thead>
          <tr>
            <th data-col="pwsid">PWSID</th>
            <th data-col="pws_name">Water System</th>
            <th data-col="county_name">County</th>
            <th data-col="size_category">Size Tier</th>
            <th class="num" data-col="samples_above_mcl_benchmark">Above MCL Benchmark</th>
            <th class="num" data-col="max_pfoa_ppt">Max PFOA (ppt)</th>
            <th class="num" data-col="max_pfos_ppt">Max PFOS (ppt)</th>
            <th class="num" data-col="max_pfhxs_ppt">Max PFHxS (ppt)</th>
            <th class="num" data-col="max_hazard_index_score">Max HI</th>
            <th data-col="screening_status">Screening Status</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </section>
</main>

<footer>
  <p><strong>Attribution:</strong> Tosson Services LLC dba Tosson Environmental Analytics &bull; Public-domain data sources:
    <a href="https://www.epa.gov/dwucmr/occurrence-data-unregulated-contaminant-monitoring-rule" target="_blank" rel="noopener">EPA UCMR 5 Occurrence Data</a> &bull;
    <a href="https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation" target="_blank" rel="noopener">2024 EPA PFAS NPDWR (89 FR 32532)</a>.
  </p>
  <p><strong>Regulatory-Status Footnote (Proposed / Not Final):</strong> All six 2024 EPA PFAS MCL screening benchmarks (PFOA 4 ppt, PFOS 4 ppt, PFHxS 10 ppt, PFNA 10 ppt, HFPO-DA 10 ppt, Hazard Index 1.0) are implemented for transparent occurrence screening. EPA has published a <strong>proposed / not final</strong> rulemaking regarding potential rescission of the PFHxS, PFNA, HFPO-DA, and Hazard Index standards while retaining PFOA and PFOS (<a href="https://www.epa.gov/sdwa/proposed-pfas-rescission-rule" target="_blank" rel="noopener">https://www.epa.gov/sdwa/proposed-pfas-rescission-rule</a>).</p>
</footer>

<script>
const DATA = {safe_json};

function esc(v) {{
  if (v === null || v === undefined) return "—";
  return String(v).replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
}}
function fmtNum(v, dec=0) {{
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString(undefined, {{minimumFractionDigits: dec, maximumFractionDigits: dec}});
}}
function badgeHtml(label) {{
  const s = String(label || "");
  if (s.includes("Above")) return `<span class="badge badge-alert">${{esc(s)}}</span>`;
  if (s.includes("Detected")) return `<span class="badge badge-warn">${{esc(s)}}</span>`;
  return `<span class="badge badge-ok">${{esc(s)}}</span>`;
}}

function renderKPIs() {{
  const k = DATA.kpis;
  const cards = [
    ["Reconciled NC Results", fmtNum(k.total_samples), "Exact match to EPA UCMR 5"],
    ["NC Counties Screened", fmtNum(k.total_counties), "Mapped via EPA SDWIS"],
    ["NC Water Systems", fmtNum(k.total_systems), "Distinct PWSIDs"],
    ["PFAS Detections (>= MRL)", fmtNum(k.total_pfas_detections), "29 PFAS monitored"],
    ["Samples Above 2024 MCL Benchmark", fmtNum(k.total_samples_above_mcl_benchmark), "Informational screening"],
    ["Systems Above Any 2024 Benchmark", fmtNum(k.total_systems_above_any_2024_benchmark), "Individual MCL or HI > 1.0"]
  ];
  document.getElementById("kpi-grid").innerHTML = cards.map(([lbl, val, sub]) => `
    <div class="kpi-card">
      <div class="kpi-label">${{esc(lbl)}}</div>
      <div class="kpi-value">${{val}}</div>
      <div class="kpi-sub">${{esc(sub)}}</div>
    </div>
  `).join("");
}}

function renderBarSvg(containerId, items, labelKey, valueKey, color) {{
  const el = document.getElementById(containerId);
  if (!items.length) {{
    el.innerHTML = "<p style='color:#94a3b8'>No records match current filter.</p>";
    return;
  }}
  const maxVal = Math.max(...items.map(d => Number(d[valueKey]) || 0), 1);
  const rowH = 26, padL = 130, padR = 56, width = 560, barW = width - padL - padR;
  const height = items.length * rowH + 14;
  const rows = items.map((d, idx) => {{
    const y = idx * rowH + 6;
    const val = Number(d[valueKey]) || 0;
    const w = Math.max(2, (val / maxVal) * barW);
    return `
      <text x="${{padL - 8}}" y="${{y + 15}}" text-anchor="end" fill="#cbd5e1" font-size="12">${{esc(d[labelKey])}}</text>
      <rect x="${{padL}}" y="${{y + 3}}" width="${{w.toFixed(1)}}" height="16" rx="3" fill="${{color}}" />
      <text x="${{(padL + w + 6).toFixed(1)}}" y="${{y + 15}}" fill="#f8fafc" font-size="12">${{fmtNum(val)}}</text>
    `;
  }}).join("");
  el.innerHTML = `<svg viewBox="0 0 ${{width}} ${{height}}" width="100%" role="img">${{rows}}</svg>`;
}}

let countySort = {{ col: "samples_above_mcl_benchmark", asc: false }};
let systemSort = {{ col: "samples_above_mcl_benchmark", asc: false }};

function sortRows(rows, sortState) {{
  const {{ col, asc }} = sortState;
  return [...rows].sort((a, b) => {{
    const va = a[col], vb = b[col];
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    if (typeof va === "number" && typeof vb === "number") return asc ? va - vb : vb - va;
    return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  }});
}}

function applyFiltersAndRender() {{
  const q = document.getElementById("countySearch").value.trim().toLowerCase();
  const status = document.getElementById("statusFilter").value;
  const analyte = document.getElementById("analyteFilter").value;

  const filteredCounties = DATA.counties.filter(c => {{
    if (q && !String(c.county_name).toLowerCase().includes(q)) return false;
    if (status !== "ALL" && c.screening_summary_label !== status) return false;
    if (analyte !== "ALL" && c.primary_exceeding_analyte !== analyte) return false;
    return true;
  }});

  const sortedCounties = sortRows(filteredCounties, countySort);
  document.getElementById("countyCountLabel").textContent = sortedCounties.length;
  document.querySelector("#countyTable tbody").innerHTML = sortedCounties.map(c => `
    <tr>
      <td><strong>${{esc(c.county_name)}}</strong></td>
      <td class="num">${{fmtNum(c.systems_monitored)}}</td>
      <td class="num">${{fmtNum(c.total_samples)}}</td>
      <td class="num">${{fmtNum(c.pfas_detected_samples)}}</td>
      <td class="num">${{fmtNum(c.samples_above_mcl_benchmark)}}</td>
      <td class="num">${{fmtNum(c.systems_above_any_2024_benchmark)}}</td>
      <td class="num">${{c.max_benchmark_ratio != null ? fmtNum(c.max_benchmark_ratio, 2) + "x" : "—"}}</td>
      <td class="num">${{fmtNum(c.max_hazard_index_score, 3)}}</td>
      <td>${{esc(c.primary_exceeding_analyte)}}</td>
      <td>${{badgeHtml(c.screening_summary_label)}}</td>
    </tr>
  `).join("");

  const countySet = new Set(filteredCounties.map(c => c.county_name));
  const filteredSystems = DATA.systems.filter(s => {{
    if (q && !(String(s.county_name).toLowerCase().includes(q) || String(s.pws_name).toLowerCase().includes(q) || String(s.pwsid).toLowerCase().includes(q))) return false;
    if ((status !== "ALL" || analyte !== "ALL") && !countySet.has(s.county_name)) return false;
    return true;
  }});

  const sortedSystems = sortRows(filteredSystems, systemSort);
  document.getElementById("systemCountLabel").textContent = sortedSystems.length;
  document.querySelector("#systemTable tbody").innerHTML = sortedSystems.slice(0, 150).map(s => `
    <tr>
      <td><code>${{esc(s.pwsid)}}</code></td>
      <td>${{esc(s.pws_name)}}</td>
      <td>${{esc(s.county_name)}}</td>
      <td>${{esc(s.size_category)}}</td>
      <td class="num">${{fmtNum(s.samples_above_mcl_benchmark)}}</td>
      <td class="num">${{fmtNum(s.max_pfoa_ppt, 2)}}</td>
      <td class="num">${{fmtNum(s.max_pfos_ppt, 2)}}</td>
      <td class="num">${{fmtNum(s.max_pfhxs_ppt, 2)}}</td>
      <td class="num">${{fmtNum(s.max_hazard_index_score, 3)}}</td>
      <td>${{badgeHtml(s.screening_status)}}</td>
    </tr>
  `).join("");

  renderBarSvg(
    "countyChart",
    sortedCounties.filter(c => c.samples_above_mcl_benchmark > 0).slice(0, 12),
    "county_name",
    "samples_above_mcl_benchmark",
    "#fb7185"
  );
  const topAnalytes = DATA.analytes
    .filter(a => a.analyte_group === "PFAS" && a.detected_samples > 0)
    .sort((a, b) => b.detected_samples - a.detected_samples)
    .slice(0, 10);
  renderBarSvg("analyteChart", topAnalytes, "contaminant", "detected_samples", "#38bdf8");
}}

function init() {{
  renderKPIs();
  const analytes = [...new Set(DATA.counties.map(c => c.primary_exceeding_analyte).filter(a => a && a !== "None"))].sort();
  const sel = document.getElementById("analyteFilter");
  analytes.forEach(a => {{
    const opt = document.createElement("option");
    opt.value = a;
    opt.textContent = a;
    sel.appendChild(opt);
  }});
  ["countySearch", "statusFilter", "analyteFilter"].forEach(id =>
    document.getElementById(id).addEventListener("input", applyFiltersAndRender)
  );
  document.querySelectorAll("#countyTable th").forEach(th => {{
    th.addEventListener("click", () => {{
      const col = th.dataset.col;
      countySort = {{ col, asc: countySort.col === col ? !countySort.asc : false }};
      applyFiltersAndRender();
    }});
  }});
  document.querySelectorAll("#systemTable th").forEach(th => {{
    th.addEventListener("click", () => {{
      const col = th.dataset.col;
      systemSort = {{ col, asc: systemSort.col === col ? !systemSort.asc : false }};
      applyFiltersAndRender();
    }});
  }});
  applyFiltersAndRender();
}}
init();
</script>
</body>
</html>
"""
    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_doc, encoding="utf-8")

    summary = {
        "generated_at_utc": generated_ts,
        "out_html": str(out_html),
        "bytes": out_html.stat().st_size,
        "counties": total_counties,
        "systems": total_systems,
        "total_samples": total_samples,
        "systems_above_any_2024_benchmark": total_sys_above,
    }

    if not skip_registry and registry_path is not None:
        upsert_entry(
            {
                "artifact_id": "a4d-pfas-html-dashboard",
                "kind": "dashboard",
                "title": "Interactive North Carolina EPA UCMR 5 PFAS Screening HTML Dashboard",
                "repo_path": "portfolio-factory/dashboard/index.html",
                "evidence": {
                    "command": ".venv/bin/python portfolio-factory/dashboard/build_dashboard.py",
                    "result": (
                        f"PASS (self-contained HTML dashboard generated: {total_counties} counties, "
                        f"{total_systems} systems, {total_samples} reconciled results, zero external CDNs)"
                    ),
                    "timestamp": generated_ts,
                    "metrics": {
                        "counties": total_counties,
                        "systems": total_systems,
                        "total_samples": total_samples,
                        "html_bytes": summary["bytes"],
                    },
                },
                "supports_claims": [
                    "Built an interactive self-contained HTML dashboard rendered directly from DuckDB dbt marts with county/analyte filters and inline SVG charts",
                    "BI Dashboards",
                    "DuckDB",
                    "EPA UCMR 5 / PFAS Analytics",
                ],
                "source_urls": [
                    "https://www.epa.gov/dwucmr/occurrence-data-unregulated-contaminant-monitoring-rule",
                    "https://www.federalregister.gov/documents/2024/04/26/2024-07773/pfas-national-primary-drinking-water-regulation",
                    "https://www.epa.gov/sdwa/proposed-pfas-rescission-rule",
                ],
            },
            registry_path=registry_path,
            workspace_root=workspace_root,
            check_path=True,
        )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build self-contained HTML dashboard from DuckDB marts.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--out-html", type=Path, default=DEFAULT_OUT_HTML)
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--skip-registry", action="store_true")
    args = parser.parse_args(argv)

    summary = build_dashboard(
        db_path=args.db_path,
        out_html=args.out_html,
        registry_path=args.registry_path,
        skip_registry=args.skip_registry,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
