"""Shared Proof Registry read/write/validation library for Sprint 5.

Provides file-locked atomic updates so parallel Build A and Build B executions
can register verified artifacts safely into proof-registry.json.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = WORKSPACE_ROOT / "proof-registry.json"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "proof_registry.schema.json"

ALLOWED_KINDS = frozenset(
    {"dbt_model", "dag", "sql_pack", "dax_library", "dashboard", "report"}
)
LEGAL_ENTITY = "Tosson Services LLC dba Tosson Environmental Analytics"
OWNER_NAME = "Temitope Soneye"
SCHEMA_VERSION = "1.0.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _blank_registry() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": _utc_now(),
        "owner": OWNER_NAME,
        "legal_entity": LEGAL_ENTITY,
        "entries": [],
    }


def validate_registry(
    data: dict[str, Any],
    *,
    workspace_root: Path | None = None,
    check_paths: bool = True,
) -> list[str]:
    """Validate registry data against JSON schema and optional path/uniqueness checks.

    Returns a list of human-readable error strings (empty list == valid).
    """
    errors: list[str] = []
    validator = Draft202012Validator(load_schema())
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"Schema error at {loc}: {err.message}")

    entries = data.get("entries")
    if isinstance(entries, list):
        seen_ids: set[str] = set()
        root = Path(workspace_root) if workspace_root is not None else WORKSPACE_ROOT
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            aid = entry.get("artifact_id")
            if aid in seen_ids:
                errors.append(f"Duplicate artifact_id at entries[{idx}]: {aid}")
            elif isinstance(aid, str):
                seen_ids.add(aid)

            if check_paths and isinstance(entry.get("repo_path"), str):
                target = root / entry["repo_path"]
                if not target.exists():
                    errors.append(
                        f"Missing repo_path for {aid}: {entry['repo_path']} (resolved: {target})"
                    )
    return errors


def load_registry(registry_path: Path | str = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    path = Path(registry_path)
    if not path.exists():
        return _blank_registry()
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".proof_registry_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=False)
            fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def init_registry(
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    *,
    overwrite: bool = False,
) -> Path:
    path = Path(registry_path)
    if path.exists() and not overwrite:
        return path
    data = _blank_registry()
    errors = validate_registry(data, check_paths=False)
    if errors:
        raise ValueError("; ".join(errors))
    _atomic_write_json(path, data)
    return path


def upsert_entry(
    entry: dict[str, Any],
    *,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    workspace_root: Path | None = None,
    check_path: bool = True,
) -> dict[str, Any]:
    """Validate and atomically insert or update an entry by artifact_id."""
    path = Path(registry_path)
    root = Path(workspace_root) if workspace_root is not None else WORKSPACE_ROOT
    lock_path = path.parent / f".{path.name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        try:
            data = load_registry(path)
            entries: list[dict[str, Any]] = list(data.get("entries", []))
            aid = entry.get("artifact_id")
            replaced = False
            for idx, existing in enumerate(entries):
                if existing.get("artifact_id") == aid:
                    entries[idx] = entry
                    replaced = True
                    break
            if not replaced:
                entries.append(entry)
            entries.sort(key=lambda item: item.get("artifact_id", ""))
            data["entries"] = entries
            data["updated_at"] = _utc_now()

            errors = validate_registry(data, workspace_root=root, check_paths=check_path)
            if errors:
                raise ValueError("Proof Registry validation failed:\n" + "\n".join(errors))

            _atomic_write_json(path, data)
            return data
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or initialize proof-registry.json")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize an empty proof-registry.json")
    p_init.add_argument("--path", default=str(DEFAULT_REGISTRY_PATH))
    p_init.add_argument("--overwrite", action="store_true")

    p_val = sub.add_parser("validate", help="Validate proof-registry.json")
    p_val.add_argument("--path", default=str(DEFAULT_REGISTRY_PATH))
    p_val.add_argument("--workspace-root", default=str(WORKSPACE_ROOT))
    p_val.add_argument("--skip-path-check", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "init":
        out = init_registry(args.path, overwrite=args.overwrite)
        print(f"Initialized proof registry at {out}")
        return 0
    if args.cmd == "validate":
        data = load_registry(args.path)
        errs = validate_registry(
            data,
            workspace_root=Path(args.workspace_root),
            check_paths=not args.skip_path_check,
        )
        if errs:
            for e in errs:
                print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(
            f"VALID: {args.path} (schema_version={data['schema_version']}, entries={len(data['entries'])})"
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
