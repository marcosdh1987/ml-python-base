"""Tests for skill discovery and internal-over-external precedence."""

from __future__ import annotations

from pathlib import Path

from ml_python_base.skills_sync.discovery import discover_skills
from ml_python_base.skills_sync.models import KIND_EXTERNAL, KIND_INTERNAL


def test_discovery_orders_internal_then_external(repo_root: Path) -> None:
    skills = discover_skills(repo_root)
    kinds = [s.kind for s in skills]
    # All internal skills come before any external skill.
    last_internal = max(
        (i for i, k in enumerate(kinds) if k == KIND_INTERNAL), default=-1
    )
    first_external = next(
        (i for i, k in enumerate(kinds) if k == KIND_EXTERNAL), len(kinds)
    )
    assert last_internal < first_external


def test_discovery_excludes_readme(repo_root: Path) -> None:
    names = {s.name for s in discover_skills(repo_root)}
    assert "README" not in names


def test_internal_skills_are_sorted(repo_root: Path) -> None:
    internal = [s.name for s in discover_skills(repo_root) if s.kind == KIND_INTERNAL]
    assert internal == sorted(internal)


def test_precedence_drops_colliding_external(tmp_path: Path) -> None:
    internal_dir = tmp_path / ".github/skills"
    external_dir = tmp_path / ".github/skills-external"
    internal_dir.mkdir(parents=True)
    (external_dir / "shared").mkdir(parents=True)

    (internal_dir / "shared.md").write_text(
        "---\nname: shared\ndescription: internal one\n---\n", encoding="utf-8"
    )
    (external_dir / "shared" / "SKILL.md").write_text(
        "---\nname: shared\ndescription: external one\n---\n", encoding="utf-8"
    )

    skills = discover_skills(tmp_path)
    shared = [s for s in skills if s.name == "shared"]
    assert len(shared) == 1
    assert shared[0].kind == KIND_INTERNAL
    assert shared[0].description == "internal one"


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_internal_bundle_is_discovered(tmp_path: Path) -> None:
    """An internal skill may be a directory whose entry point is SKILL.md."""
    _write(
        tmp_path / ".github/skills/bundled/SKILL.md",
        "---\nname: bundled\ndescription: runs a script\n---\n",
    )
    _write(tmp_path / ".github/skills/bundled/run.sh", "#!/bin/sh\necho hi\n")

    skills = discover_skills(tmp_path)

    assert [s.name for s in skills] == ["bundled"]
    assert skills[0].kind == KIND_INTERNAL
    assert skills[0].is_bundle
    assert skills[0].source_path == tmp_path / ".github/skills/bundled"
    assert skills[0].description == "runs a script"


def test_internal_flat_file_is_not_a_bundle(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github/skills/flat.md",
        "---\nname: flat\ndescription: prose only\n---\n",
    )

    skills = discover_skills(tmp_path)

    assert not skills[0].is_bundle
    assert skills[0].source_path == tmp_path / ".github/skills/flat.md"


def test_internal_directory_without_skill_md_is_skipped(tmp_path: Path) -> None:
    """A folder that lacks the entry point is not a skill."""
    _write(tmp_path / ".github/skills/notaskill/helper.py", "x = 1\n")
    _write(
        tmp_path / ".github/skills/real.md",
        "---\nname: real\ndescription: d\n---\n",
    )

    assert [s.name for s in discover_skills(tmp_path)] == ["real"]


def test_mixed_internal_shapes_sort_by_skill_name(tmp_path: Path) -> None:
    """Ordering is by skill name, so both shapes interleave predictably."""
    _write(
        tmp_path / ".github/skills/alpha.md", "---\nname: alpha\ndescription: a\n---\n"
    )
    _write(
        tmp_path / ".github/skills/beta/SKILL.md",
        "---\nname: beta\ndescription: b\n---\n",
    )
    _write(
        tmp_path / ".github/skills/gamma.md", "---\nname: gamma\ndescription: g\n---\n"
    )

    assert [s.name for s in discover_skills(tmp_path)] == ["alpha", "beta", "gamma"]
