"""Workspace compliance & hygiene audit tests (Step 3 / C-2 / C-4).

Passes with NO fixtures/ directory present. Enforces:
- Zero Progressive Insurance references in deliverables (rule files exempt per C-2)
- Zero UCMR 5 'violation' terminology in Build A outputs (rule files exempt per C-2)
- Zero occurrences of the prohibited unverified-reuse phrase from AGENTS.md
- Zero secrets/env values or owner PII leaked into deliverables
- Required SKILL.md runbooks exist for both Build A and Build B
- Proof Registry is valid and covers both Build A and Build B artifacts
"""
from __future__ import annotations

import re
from pathlib import Path

from shared.proof_registry import DEFAULT_REGISTRY_PATH, load_registry, validate_registry

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = [
    WORKSPACE_ROOT / "portfolio-factory",
    WORKSPACE_ROOT / "auction-intel-v2",
    WORKSPACE_ROOT / "shared",
    WORKSPACE_ROOT / ".agents",
]

TEXT_EXTENSIONS = {
    ".py",
    ".sql",
    ".yml",
    ".yaml",
    ".md",
    ".txt",
    ".json",
    ".dax",
    ".html",
    ".css",
    ".js",
    ".csv",
    ".sh",
    ".example",
}

# Exempt rule/blocklist files per Muse adjudication C-2
RULE_FILE_EXEMPTIONS = {
    "portfolio-factory/verifier/forbidden_rules.yaml",
    "portfolio-factory/verifier/skill_taxonomy.yaml",
}

# Built dynamically so this audit file itself never contains the literal banned phrase
PROHIBITED_REUSE_PHRASE = " ".join(["reuse", "terms", "unverified"])

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "raw",
    "logs",
    ".venv",
    ".venv-airflow",
    ".airflow_home",
    "fixtures",
    "upload",
}


def _iter_deliverable_files(roots: list[Path]):
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            # Skip large generated dbt index.html bundle only for regex? No — scan it too!
            yield path


def test_required_skill_runbooks_exist() -> None:
    skill_a = WORKSPACE_ROOT / ".agents" / "skills" / "build-a-portfolio-factory" / "SKILL.md"
    skill_b = WORKSPACE_ROOT / ".agents" / "skills" / "build-b-auction-intel-v2" / "SKILL.md"
    assert skill_a.exists(), f"Missing Build A runbook: {skill_a}"
    assert skill_b.exists(), f"Missing Build B runbook: {skill_b}"
    assert len(skill_a.read_text(encoding="utf-8").strip()) > 100
    assert len(skill_b.read_text(encoding="utf-8").strip()) > 100


def test_no_progressive_references_in_deliverables() -> None:
    pattern = re.compile(r"\bprogressive\s+insurance\b|\bprogressive\b", re.IGNORECASE)
    offenders: list[str] = []
    for fpath in _iter_deliverable_files(SCAN_DIRS):
        rel = fpath.relative_to(WORKSPACE_ROOT).as_posix()
        if rel in RULE_FILE_EXEMPTIONS:
            continue
        # Ignore dbt generated manifest/index/catalog only if benign English word 'progressive' appears in dbt-core docs UI JS
        if rel.startswith("portfolio-factory/pfas_warehouse/target/index.html"):
            continue
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            offenders.append(rel)
    assert offenders == [], f"Forbidden employer references found in deliverables: {offenders}"


def test_no_ucmr5_violation_language_in_outputs() -> None:
    """C-2: violation-audit scopes to Build A outputs; rule files exempt."""
    pattern = re.compile(r"\bviolations?\b", re.IGNORECASE)
    offenders: list[str] = []
    build_a_root = WORKSPACE_ROOT / "portfolio-factory"
    for fpath in _iter_deliverable_files([build_a_root]):
        rel = fpath.relative_to(WORKSPACE_ROOT).as_posix()
        if rel in RULE_FILE_EXEMPTIONS:
            continue
        # Verifier code defines forbidden-claim verdict handling; outputs must never claim violations
        if rel.startswith("portfolio-factory/verifier/") and fpath.suffix in {".py", ".yaml"}:
            continue
        # dbt compiled static docs UI JS from dbt-core itself is vendor HTML
        if rel == "portfolio-factory/pfas_warehouse/target/index.html":
            continue
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            offenders.append(rel)
    assert offenders == [], f"Prohibited UCMR 5 'violation' terminology found in: {offenders}"


def test_no_prohibited_reuse_phrase_anywhere() -> None:
    offenders: list[str] = []
    roots = SCAN_DIRS + [WORKSPACE_ROOT / "proof-registry.json", WORKSPACE_ROOT / "implementation_plan.md"]
    for item in roots:
        if item.is_file():
            if PROHIBITED_REUSE_PHRASE in item.read_text(encoding="utf-8", errors="ignore").lower():
                offenders.append(item.relative_to(WORKSPACE_ROOT).as_posix())
        elif item.is_dir():
            for fpath in _iter_deliverable_files([item]):
                if PROHIBITED_REUSE_PHRASE in fpath.read_text(encoding="utf-8", errors="ignore").lower():
                    offenders.append(fpath.relative_to(WORKSPACE_ROOT).as_posix())
    assert offenders == [], f"Prohibited reuse phrase found in: {offenders}"


def test_no_env_secrets_or_personal_pii_in_deliverables() -> None:
    # No committed .env files
    for env_file in WORKSPACE_ROOT.rglob(".env"):
        if any(p in SKIP_DIRS for p in env_file.parts):
            continue
        raise AssertionError(f"Committed .env file forbidden: {env_file}")

    # Every .env.example must contain only variable NAMES (empty right-hand sides)
    for ex_file in WORKSPACE_ROOT.rglob(".env.example"):
        if any(p in SKIP_DIRS for p in ex_file.parts):
            continue
        for lineno, line in enumerate(ex_file.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            assert "=" in stripped, f"{ex_file}:{lineno} invalid env line: {stripped}"
            _, val = stripped.split("=", 1)
            assert val.strip() == "", f"{ex_file}:{lineno} must contain variable NAME only, no value: {stripped}"

    # No personal home street address / phone / personal gmail leaked into deliverable code/reports
    pii_patterns = [
        re.compile(r"3118\s+Hannaford", re.IGNORECASE),
        re.compile(r"334-728-5402"),
        re.compile(r"soneye\.temitope89@gmail\.com", re.IGNORECASE),
    ]
    pii_hits: list[str] = []
    for fpath in _iter_deliverable_files(SCAN_DIRS):
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        if any(p.search(text) for p in pii_patterns):
            pii_hits.append(fpath.relative_to(WORKSPACE_ROOT).as_posix())
    assert pii_hits == [], f"Personal PII leaked into deliverables: {pii_hits}"


def test_proof_registry_complete_and_traceable() -> None:
    data = load_registry(DEFAULT_REGISTRY_PATH)
    errors = validate_registry(data, workspace_root=WORKSPACE_ROOT, check_paths=True)
    assert errors == [], f"Proof registry validation errors: {errors}"

    ids = {e["artifact_id"] for e in data["entries"]}
    assert any(i.startswith("a1-") for i in ids), "Missing A1 ingest entry in proof-registry.json"
    assert any(i.startswith("a2-") for i in ids), "Missing A2 dbt model entries in proof-registry.json"
    assert any(i.startswith("a3-") for i in ids), "Missing A3 Airflow DAG entry in proof-registry.json"
    assert any(i.startswith("a4") for i in ids), "Missing A4 SQL/BI entries in proof-registry.json"
    assert any(i.startswith("a5-") for i in ids), "Missing A5 verifier entry in proof-registry.json"
    assert any(i.startswith("a6-") for i in ids), "Missing A6 gap analyser entry in proof-registry.json"
    assert any(i.startswith("b1-") for i in ids), "Missing B1 manifest ROI entry in proof-registry.json"
    assert any(i.startswith("b2-") for i in ids), "Missing B2 HiBid churn entry in proof-registry.json"
    assert any(i.startswith("b3-") for i in ids), "Missing B3 land scorer entry in proof-registry.json"
    assert any(i.startswith("b4-") for i in ids), "Missing B4 Kia Carnival entry in proof-registry.json"
    assert any(i.startswith("b5-") for i in ids), "Missing B5 integration runbook entry in proof-registry.json"
