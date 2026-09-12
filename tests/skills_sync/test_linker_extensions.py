"""Projection into a *foreign* root: the strategy override and ``add_skills``.

Both exist for one consumer shape — a harness projected into a repository that
does not own the skills (the harness lab placing governed skills into a cloned
target workspace). They are part of the engine's public surface because a
downstream that had to re-implement them would fork the linker, and a forked
linker silently loses the catalog rules tested here (legacy filtering,
overlays).
"""

from __future__ import annotations

from pathlib import Path

from ml_python_base.skills_sync.discovery import discover_skills
from ml_python_base.skills_sync.linker import add_skills, link_tool
from ml_python_base.skills_sync.models import (
    LINK_COPY,
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
            overlays={"old": {"visibility": "legacy", "replacement": "plain"}},
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


def _seed_source(root: Path) -> None:
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


def _claude_tool() -> ToolSpec:
    return ToolSpec(
        id="claude",
        display_name="Claude Code",
        link_strategy="symlink",
        native_skills_dir=".claude/skills",
    )


def test_strategy_override_copies_into_a_foreign_root(tmp_path: Path) -> None:
    """A symlink tool projected elsewhere must copy: a link would dangle."""
    source = tmp_path / "harness"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _seed_source(source)
    skills = discover_skills(source, registry=_registry())

    link_tool(target, _claude_tool(), skills, strategy=LINK_COPY)

    projected = target / ".claude/skills/plain/SKILL.md"
    assert projected.is_file() and not projected.is_symlink()
    assert "plain one" in projected.read_text(encoding="utf-8")


def test_foreign_projection_keeps_overlays_and_drops_legacy(tmp_path: Path) -> None:
    source = tmp_path / "harness"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _seed_source(source)
    skills = discover_skills(source, registry=_registry())

    link_tool(target, _claude_tool(), skills, strategy=LINK_COPY)

    names = sorted(p.name for p in (target / ".claude/skills").iterdir())
    assert names == ["plain", "vendored"]  # `old` is legacy: never projected
    overlaid = (target / ".claude/skills/vendored/SKILL.md").read_text(encoding="utf-8")
    assert BANNER_TITLE in overlaid
    assert "Never run git commit unless asked." in overlaid


def test_overlay_banner_names_the_governed_path_from_a_foreign_root(
    tmp_path: Path,
) -> None:
    """The source is outside the projection root; the label must not raise."""
    source = tmp_path / "harness"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _seed_source(source)
    vendored = next(
        s for s in discover_skills(source, registry=_registry()) if s.name == "vendored"
    )

    text = render_overlay(target, vendored)

    assert ".github/skills-external/vendored/SKILL.md" in text
    assert str(tmp_path) not in text  # no absolute path leaks into the banner


def test_add_skills_does_not_prune_the_foreign_view(tmp_path: Path) -> None:
    """Adding one skill must leave the target team's own skills in place."""
    source = tmp_path / "harness"
    target = tmp_path / "target"
    source.mkdir()
    _seed_source(source)
    theirs = target / ".claude/skills/their_own"
    theirs.mkdir(parents=True)
    (theirs / "SKILL.md").write_text("theirs\n", encoding="utf-8")

    skills = [
        s for s in discover_skills(source, registry=_registry()) if s.name == "plain"
    ]
    hashes = add_skills(target, _claude_tool(), skills)

    assert (theirs / "SKILL.md").read_text(encoding="utf-8") == "theirs\n"
    assert (target / ".claude/skills/plain/SKILL.md").is_file()
    assert list(hashes) == ["plain"]


def test_add_skills_applies_the_catalog_rules(tmp_path: Path) -> None:
    """A legacy skill is not added, and an overlaid one is added overlaid."""
    source = tmp_path / "harness"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _seed_source(source)
    skills = discover_skills(source, registry=_registry())

    hashes = add_skills(target, _claude_tool(), skills)

    assert "old" not in hashes
    assert BANNER_TITLE in (target / ".claude/skills/vendored/SKILL.md").read_text(
        encoding="utf-8"
    )


def test_link_tool_without_an_override_still_obeys_the_registry(
    tmp_path: Path,
) -> None:
    """The override is opt-in: the declared strategy is unchanged by its presence."""
    _seed_source(tmp_path)
    skills = discover_skills(tmp_path, registry=_registry())

    link_tool(tmp_path, _claude_tool(), skills)

    assert (tmp_path / ".claude/skills/plain/SKILL.md").is_symlink()


def test_render_tool_reads_templates_from_a_foreign_template_root(
    tmp_path: Path,
) -> None:
    """Rendering into a target that owns neither templates nor governed skills."""
    from ml_python_base.skills_sync.renderer import (
        BEGIN_MARKER,
        END_MARKER,
        render_tool,
    )

    source = tmp_path / "harness"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _seed_source(source)
    templates = source / "adapters/templates"
    templates.mkdir(parents=True)
    shared = Path(__file__).resolve().parents[2] / "adapters/templates"
    for name in ("_skills_block.j2", "claude.md.j2"):
        (templates / name).write_text(
            (shared / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    tool = ToolSpec(
        id="claude",
        display_name="Claude Code",
        link_strategy="symlink",
        native_skills_dir=".claude/skills",
        adapter_file="CLAUDE.md",
        adapter_template="claude.md.j2",
    )
    registry = Registry(
        schema_version=1,
        governance=Governance(files=(), automation="", orchestration=""),
        tools=(tool,),
        catalog=_registry().catalog,
    )
    (target / "CLAUDE.md").write_text(
        f"# Target\n\n{BEGIN_MARKER}\n{END_MARKER}\n", encoding="utf-8"
    )

    assert render_tool(target, registry, tool, template_root=source) is True

    body = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "`plain`" in body
    assert "`old`" not in body.split("Legacy names")[0]  # legacy stays out of the lists
