"""Tests for projection-time overlays and legacy filtering in the linker."""

from __future__ import annotations

import os
from pathlib import Path

from ml_python_base.skills_sync.catalog import apply_registry
from ml_python_base.skills_sync.discovery import discover_skills
from ml_python_base.skills_sync.linker import (
    expected_overlay_files,
    link_tool,
    stale_native_entries,
)
from ml_python_base.skills_sync.models import (
    CatalogSpec,
    Governance,
    Policy,
    Registry,
    ToolSpec,
)
from ml_python_base.skills_sync.overlay import BANNER_TITLE, render_overlay

VENDOR = """---
name: vendored
description: "You MUST use this before ANY creative work."
---

# Vendored

Step 6: commit the design document to git.
"""


def _registry() -> Registry:
    return Registry(
        schema_version=1,
        governance=Governance(files=(), automation="", orchestration=""),
        tools=(),
        catalog=CatalogSpec(
            overlays={
                "vendored": {"description": "Use for design-impacting work only."},
                "old": {"visibility": "legacy", "replacement": "plain"},
            },
            policies=(
                Policy(
                    id="git-actions",
                    title="Git actions are recommendations",
                    summary="Never run git commit unless asked.",
                    applies_to=("vendored",),
                ),
            ),
        ),
    )


def _seed(root: Path) -> None:
    internal = root / ".github/skills"
    internal.mkdir(parents=True)
    (internal / "plain.md").write_text(
        "---\nname: plain\ndescription: plain one\n---\nbody\n", encoding="utf-8"
    )
    (internal / "old.md").write_text(
        "---\nname: old\ndescription: retired\n---\nbody\n", encoding="utf-8"
    )
    vendored = root / ".github/skills-external/vendored"
    vendored.mkdir(parents=True)
    (vendored / "SKILL.md").write_text(VENDOR, encoding="utf-8")
    (vendored / "helper.md").write_text("helper\n", encoding="utf-8")


def _symlink_tool() -> ToolSpec:
    return ToolSpec(
        id="claude",
        display_name="Claude Code",
        link_strategy="symlink",
        native_skills_dir=".claude/skills",
    )


def _copy_tool() -> ToolSpec:
    return ToolSpec(
        id="antigravity",
        display_name="Antigravity",
        link_strategy="copy",
        native_skills_dir=".agents/skills",
        needs_manifest=True,
        manifest_path=".agents/skills/.generated-manifest.tsv",
    )


def test_overlay_renders_governed_frontmatter_banner_and_vendor_body(
    tmp_path: Path,
) -> None:
    _seed(tmp_path)
    skills = discover_skills(tmp_path, registry=_registry())
    vendored = next(s for s in skills if s.name == "vendored")

    text = render_overlay(tmp_path, vendored)

    assert text.startswith('---\nname: vendored\ndescription: "Use for design-')
    assert BANNER_TITLE in text
    assert "Never run git commit unless asked." in text
    assert ".github/skills-external/vendored/SKILL.md" in text
    assert "Step 6: commit the design document to git." in text  # verbatim body
    assert "You MUST use this" not in text.split("---", 2)[1]  # frontmatter replaced


def test_symlink_tool_writes_overlay_file_and_links_the_rest(tmp_path: Path) -> None:
    _seed(tmp_path)
    skills = discover_skills(tmp_path, registry=_registry())
    link_tool(tmp_path, _symlink_tool(), skills)

    dest = tmp_path / ".claude/skills/vendored"
    assert (dest / "SKILL.md").is_file() and not (dest / "SKILL.md").is_symlink()
    assert BANNER_TITLE in (dest / "SKILL.md").read_text(encoding="utf-8")
    assert os.readlink(dest / "helper.md").endswith(
        "skills-external/vendored/helper.md"
    )
    # A plain skill is still a symlink.
    assert (tmp_path / ".claude/skills/plain/SKILL.md").is_symlink()
    # The vendor source is untouched.
    assert (tmp_path / ".github/skills-external/vendored/SKILL.md").read_text(
        encoding="utf-8"
    ) == VENDOR


def test_legacy_skill_is_not_projected_and_stale_link_is_removed(
    tmp_path: Path,
) -> None:
    _seed(tmp_path)
    skills = discover_skills(tmp_path, registry=_registry())
    stale = tmp_path / ".claude/skills/old"
    stale.mkdir(parents=True)
    (stale / "SKILL.md").write_text("left over", encoding="utf-8")

    link_tool(tmp_path, _symlink_tool(), skills)

    assert not stale.exists()
    assert sorted(p.name for p in (tmp_path / ".claude/skills").iterdir()) == [
        "plain",
        "vendored",
    ]


def test_copy_tool_overlays_and_hash_reflects_the_projected_content(
    tmp_path: Path,
) -> None:
    _seed(tmp_path)
    plain_registry = Registry(
        schema_version=1,
        governance=Governance(files=(), automation="", orchestration=""),
        tools=(),
    )
    without = link_tool(
        tmp_path, _copy_tool(), discover_skills(tmp_path, registry=plain_registry)
    )
    with_overlay = link_tool(
        tmp_path, _copy_tool(), discover_skills(tmp_path, registry=_registry())
    )

    copied = tmp_path / ".agents/skills/vendored/SKILL.md"
    assert BANNER_TITLE in copied.read_text(encoding="utf-8")
    assert without["vendored"] != with_overlay["vendored"]
    assert without["plain"] == with_overlay["plain"]
    assert "old" not in with_overlay


def test_expected_overlay_files_and_stale_entries_drive_the_drift_check(
    tmp_path: Path,
) -> None:
    _seed(tmp_path)
    skills = discover_skills(tmp_path, registry=_registry())
    tool = _symlink_tool()
    link_tool(tmp_path, tool, skills)

    expected = expected_overlay_files(tmp_path, tool, skills)
    assert list(expected) == [tmp_path / ".claude/skills/vendored/SKILL.md"]
    assert stale_native_entries(tmp_path, tool, skills) == []

    (tmp_path / ".claude/skills/old").mkdir()
    assert stale_native_entries(tmp_path, tool, skills) == [".claude/skills/old"]


def test_replacing_a_symlink_with_an_overlay_and_back_is_idempotent(
    tmp_path: Path,
) -> None:
    """Toggling a policy on and off must not leave a mixed state behind."""
    _seed(tmp_path)
    plain_registry = Registry(
        schema_version=1,
        governance=Governance(files=(), automation="", orchestration=""),
        tools=(),
    )
    tool = _symlink_tool()
    link_tool(tmp_path, tool, discover_skills(tmp_path, registry=plain_registry))
    entry = tmp_path / ".claude/skills/vendored/SKILL.md"
    assert entry.is_symlink()

    skills = discover_skills(tmp_path, registry=_registry())
    link_tool(tmp_path, tool, skills)
    assert entry.is_file() and not entry.is_symlink()

    link_tool(tmp_path, tool, apply_registry(skills, plain_registry))
    assert entry.is_symlink()
