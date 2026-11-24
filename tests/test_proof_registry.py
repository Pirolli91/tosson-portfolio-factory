"""Tests for the Shared Proof Registry (Step 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from shared.proof_registry import (
    DEFAULT_REGISTRY_PATH,
    init_registry,
    load_registry,
    upsert_entry,
    validate_registry,
)


def _sample_entry(repo_path: str = "dummy.txt", artifact_id: str = "a1-sample") -> dict:
    return {
        "artifact_id": artifact_id,
        "kind": "report",
        "title": "Sample Verified Artifact",
        "repo_path": repo_path,
        "evidence": {
            "command": "python3 script.py",
            "result": "PASS (rows=100)",
            "timestamp": "2026-11-23T16:00:00Z",
            "metrics": {"rows": 100},
        },
        "supports_claims": ["Sample verifiable claim"],
        "source_urls": ["https://www.epa.gov/dwucmr"],
    }


def test_init_and_upsert_valid(tmp_path: Path) -> None:
    artifact_file = tmp_path / "dummy.txt"
    artifact_file.write_text("ok", encoding="utf-8")
    reg_path = tmp_path / "proof-registry.json"

    init_registry(reg_path)
    data = upsert_entry(
        _sample_entry("dummy.txt", "a1-ingest"),
        registry_path=reg_path,
        workspace_root=tmp_path,
    )
    assert len(data["entries"]) == 1
    assert data["entries"][0]["artifact_id"] == "a1-ingest"

    # Upsert same artifact_id updates in place without duplicating
    updated = _sample_entry("dummy.txt", "a1-ingest")
    updated["title"] = "Updated Title"
    data2 = upsert_entry(updated, registry_path=reg_path, workspace_root=tmp_path)
    assert len(data2["entries"]) == 1
    assert data2["entries"][0]["title"] == "Updated Title"


def test_rejects_missing_repo_path(tmp_path: Path) -> None:
    reg_path = tmp_path / "proof-registry.json"
    init_registry(reg_path)
    with pytest.raises(ValueError, match="Missing repo_path"):
        upsert_entry(
            _sample_entry("does-not-exist.sql", "a2-missing"),
            registry_path=reg_path,
            workspace_root=tmp_path,
            check_path=True,
        )


def test_rejects_invalid_kind(tmp_path: Path) -> None:
    (tmp_path / "dummy.txt").write_text("ok", encoding="utf-8")
    reg_path = tmp_path / "proof-registry.json"
    init_registry(reg_path)
    bad = _sample_entry("dummy.txt", "bad-kind")
    bad["kind"] = "fabricated_kind"
    with pytest.raises(ValueError, match="Schema error"):
        upsert_entry(bad, registry_path=reg_path, workspace_root=tmp_path)


def test_rejects_empty_claims(tmp_path: Path) -> None:
    (tmp_path / "dummy.txt").write_text("ok", encoding="utf-8")
    reg_path = tmp_path / "proof-registry.json"
    init_registry(reg_path)
    bad = _sample_entry("dummy.txt", "empty-claims")
    bad["supports_claims"] = []
    with pytest.raises(ValueError, match="Schema error"):
        upsert_entry(bad, registry_path=reg_path, workspace_root=tmp_path)


def test_workspace_proof_registry_is_valid() -> None:
    data = load_registry(DEFAULT_REGISTRY_PATH)
    errors = validate_registry(data, check_paths=True)
    assert errors == [], f"Registry errors: {errors}"
