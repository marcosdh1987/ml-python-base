"""Tests for registry parsing and synchronization ownership metadata."""

from __future__ import annotations

from pathlib import Path

import pytest

from ml_python_base.skills_sync.config import load_registry
from ml_python_base.skills_sync.errors import RegistryError

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_registry(path: Path, template_sync: str = "") -> None:
    path.write_text(
        """
schema_version = 1

[governance]
files = []
automation = ""
orchestration = ""

[[tool]]
id = "demo"
display_name = "Demo"
link_strategy = "none"
"""
        + template_sync,
        encoding="utf-8",
    )


def test_repository_registry_declares_sync_protocol_and_disjoint_channels() -> None:
    registry = load_registry(REPO_ROOT / "adapters/registry.toml")

    assert registry.template_sync.protocol == 1
    assert ".github/skills" in registry.template_sync.governance_paths
    assert "src/ml_python_base/skills_sync" in registry.template_sync.platform_paths
    assert not (
        set(registry.template_sync.governance_paths)
        & set(registry.template_sync.platform_paths)
    )


def test_registry_without_template_sync_metadata_is_legacy_compatible(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "registry.toml"
    _write_registry(registry_path)

    registry = load_registry(registry_path)

    assert registry.template_sync.protocol == 0
    assert registry.template_sync.governance_paths == ()
    assert registry.template_sync.platform_paths == ()


def test_registry_rejects_overlapping_sync_channels(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.toml"
    _write_registry(
        registry_path,
        """

[template_sync]
protocol = 1
governance_paths = ["shared"]
platform_paths = ["shared"]
""",
    )

    with pytest.raises(RegistryError, match="overlap"):
        load_registry(registry_path)
