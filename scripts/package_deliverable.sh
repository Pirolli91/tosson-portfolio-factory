#!/usr/bin/env bash
set -euo pipefail

# Package Sprint 5 deliverables into a clean zip for Muse's shadow run.
# Excludes fixtures/, upload/, .venv*, .airflow_home/, *.duckdb*, raw caches, and caches (C-4).

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_ZIP="${1:-${WORKSPACE_DIR}/sprint5-deliverable-2026-11-23.zip}"
PYTHON_BIN="${WORKSPACE_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

"${PYTHON_BIN}" - "${WORKSPACE_DIR}" "${OUT_ZIP}" <<'PY'
import os
import sys
import zipfile
from pathlib import Path

workspace = Path(sys.argv[1]).resolve()
out_zip = Path(sys.argv[2]).resolve()

# Top-level items explicitly included in the deliverable bundle
INCLUDE_ROOTS = [
    "AGENTS.md",
    "SPRINT5-SPEC-2026-11-23.md",
    "implementation_plan.md",
    "requirements.txt",
    "requirements-airflow.txt",
    "pytest.ini",
    "proof-registry.json",
    "shared",
    "portfolio-factory",
    "auction-intel-v2",
    ".agents",
    "tests",
    "scripts",
]

EXCLUDED_DIR_NAMES = {
    "fixtures",
    "upload",
    ".venv",
    ".venv-airflow",
    ".airflow_home",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "logs",
    "dbt_packages",
}

EXCLUDED_REL_PREFIXES = (
    "portfolio-factory/warehouse/raw",
    "portfolio-factory/pfas_warehouse/logs",
)

EXCLUDED_SUFFIXES = (
    ".duckdb",
    ".duckdb.wal",
    ".duckdb.tmp",
    ".pyc",
    ".pyo",
    ".lock",
    ".zip",
)


def is_excluded(rel: Path) -> bool:
    rel_posix = rel.as_posix()
    for part in rel.parts:
        if part in EXCLUDED_DIR_NAMES:
            return True
    for prefix in EXCLUDED_REL_PREFIXES:
        if rel_posix == prefix or rel_posix.startswith(prefix + "/"):
            return True
    if any(rel_posix.endswith(suf) for suf in EXCLUDED_SUFFIXES):
        return True
    if rel.name == ".env":
        return True
    return False


if out_zip.exists():
    out_zip.unlink()

added = []
with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for item in INCLUDE_ROOTS:
        path = workspace / item
        if not path.exists():
            continue
        if path.is_file():
            rel = path.relative_to(workspace)
            if not is_excluded(rel):
                zf.write(path, rel.as_posix())
                added.append(rel.as_posix())
        else:
            for root, dirs, files in os.walk(path):
                root_path = Path(root)
                rel_root = root_path.relative_to(workspace)
                # Prune excluded directories in-place
                dirs[:] = sorted(
                    d for d in dirs if not is_excluded(rel_root / d)
                )
                for fname in sorted(files):
                    fpath = root_path / fname
                    rel = fpath.relative_to(workspace)
                    if is_excluded(rel):
                        continue
                    zf.write(fpath, rel.as_posix())
                    added.append(rel.as_posix())

# Verify zip hygiene
with zipfile.ZipFile(out_zip, "r") as zf:
    names = zf.namelist()
    bad = [
        n
        for n in names
        if n.startswith("fixtures/")
        or "/fixtures/" in n
        or ".airflow_home" in n
        or ".venv" in n
        or n.endswith(".duckdb")
        or n.endswith(".duckdb.wal")
        or "warehouse/raw/" in n
    ]
    if bad:
        raise SystemExit(f"ERROR: Forbidden entries found in zip: {bad[:10]}")

print(f"PACKAGED OK: {out_zip} ({len(added)} files, {out_zip.stat().st_size:,} bytes)")
PY
