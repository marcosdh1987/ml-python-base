"""Materialize each tool's native skills view (symlink, copy, or none).

Reconciliation is declarative: the engine computes the *desired* set of skill
directories for a tool and removes anything else it owns under the native dir
(stale cleanup), then (re)creates the desired entries. This replaces the brittle
``find -type l -delete`` + manifest-diff bash while preserving identical output
for a clean skill set.

Two catalog rules apply here:

* ``legacy`` skills are never projected — the adapter file maps their name to
  the replacement instead, so they cannot compete in discovery.
* A skill with a policy or an overridden description gets a *generated*
  ``SKILL.md`` (see :mod:`overlay`) instead of a link to the vendor file.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from ml_python_base.skills_sync.errors import UnsafeTargetError
from ml_python_base.skills_sync.hashing import folder_hash
from ml_python_base.skills_sync.models import (
    LINK_COPY,
    LINK_SYMLINK,
    Skill,
    ToolSpec,
)
from ml_python_base.skills_sync.overlay import render_overlay

# Files the engine must never delete during reconciliation.
_PROTECTED_NAMES = frozenset({".generated-manifest.tsv"})
SKILL_FILE = "SKILL.md"


def projected_skills(skills: list[Skill]) -> list[Skill]:
    """The subset of ``skills`` that native views materialize."""
    return [skill for skill in skills if skill.meta.is_projected]


def link_tool(
    root: Path,
    tool: ToolSpec,
    skills: list[Skill],
    strategy: str | None = None,
) -> dict[str, str]:
    """Project ``skills`` into ``tool``'s native view.

    Returns a ``{skill_name: folder_hash}`` mapping for tools that need a
    manifest; an empty mapping otherwise.

    ``strategy`` overrides the tool's declared ``link_strategy``. It exists for
    one case: projecting a harness into a **foreign** root (a cloned target
    repository), where a symlink would encode a path relative to a root the
    skills do not live under, so the copy strategy is the only correct one.
    Callers projecting in place must leave it unset, so the registry stays the
    single source of truth for how a tool is materialized.
    """
    if not tool.has_native_view:
        return {}

    effective = strategy or tool.link_strategy
    skills = projected_skills(skills)
    dest_root = root / tool.native_skills_dir
    dest_root.mkdir(parents=True, exist_ok=True)
    desired = {skill.name for skill in skills}
    _remove_stale(dest_root, desired)

    hashes: dict[str, str] = {}
    for skill in skills:
        if effective == LINK_SYMLINK:
            _link_symlink(root, dest_root, tool, skill)
        elif effective == LINK_COPY:
            hashes[skill.name] = _link_copy(root, dest_root, skill)
    return hashes


def add_skills(root: Path, tool: ToolSpec, skills: list[Skill]) -> dict[str, str]:
    """Copy ``skills`` into ``tool``'s native view **without pruning** it.

    :func:`link_tool` owns the view it writes: anything outside the desired set
    is removed, which is right for a repository's own directories and
    destructive in a foreign one. A target repository's ``.claude/skills/`` is
    that team's work, and adding one skill by deleting the rest would measure
    something other than the addition.

    Copies rather than symlinks, for the reason the copy strategy exists: the
    workspace has to stand on its own once the projecting repository is out of
    reach. Overlays and the legacy filter apply exactly as in ``link_tool``.
    """
    if not tool.has_native_view:
        return {}
    dest_root = root / tool.native_skills_dir
    dest_root.mkdir(parents=True, exist_ok=True)
    return {
        skill.name: _link_copy(root, dest_root, skill)
        for skill in projected_skills(skills)
    }


def expected_overlay_files(
    root: Path, tool: ToolSpec, skills: list[Skill]
) -> dict[Path, str]:
    """``{path: content}`` of every generated ``SKILL.md`` a symlink tool owns.

    Copy tools are covered by their manifest hash; symlink tools have no
    manifest, so the drift check compares these files directly.
    """
    if not tool.has_native_view or tool.link_strategy != LINK_SYMLINK:
        return {}
    dest_root = root / tool.native_skills_dir
    return {
        dest_root / skill.name / SKILL_FILE: render_overlay(root, skill)
        for skill in projected_skills(skills)
        if skill.needs_overlay
    }


def stale_native_entries(root: Path, tool: ToolSpec, skills: list[Skill]) -> list[str]:
    """Native entries that should not exist (e.g. a legacy skill still linked)."""
    if not tool.has_native_view:
        return []
    dest_root = root / tool.native_skills_dir
    if not dest_root.is_dir():
        return []
    desired = {skill.name for skill in projected_skills(skills)}
    return sorted(
        (dest_root / child.name).relative_to(root).as_posix()
        for child in dest_root.iterdir()
        if child.name not in _PROTECTED_NAMES and child.name not in desired
    )


def _remove_stale(dest_root: Path, desired: set[str]) -> None:
    for child in dest_root.iterdir():
        if child.name in _PROTECTED_NAMES:
            continue
        if child.name in desired:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def _relative_prefix(native_skills_dir: str) -> str:
    """Compute the ``../`` prefix from ``<native>/<skill>/`` back to repo root.

    e.g. ``.claude/skills`` (2 parts) + the per-skill dir => ``../../../``.
    """
    depth = len(Path(native_skills_dir).parts) + 1
    return "../" * depth


def _link_symlink(root: Path, dest_root: Path, tool: ToolSpec, skill: Skill) -> None:
    prefix = _relative_prefix(tool.native_skills_dir)
    skill_dest = dest_root / skill.name
    _ensure_owned_dir(skill_dest)
    skill_dest.mkdir(parents=True, exist_ok=True)

    if not skill.is_bundle:
        # <name>.md -> <native>/<name>/SKILL.md
        target = f"{prefix}{_repo_relative(root, skill.source_path)}"
        _materialize_skill_file(root, skill, skill_dest / SKILL_FILE, target)
        return

    # Bundle: link every top-level item of the source directory.
    for item in sorted(skill.source_path.iterdir(), key=lambda p: p.name):
        target = f"{prefix}{_repo_relative(root, item)}"
        if item.name == SKILL_FILE:
            _materialize_skill_file(root, skill, skill_dest / item.name, target)
        else:
            _symlink(skill_dest / item.name, target)


def _materialize_skill_file(
    root: Path, skill: Skill, link_path: Path, target: str
) -> None:
    """Link the entry point, or write the generated overlay in its place."""
    if not skill.needs_overlay:
        _symlink(link_path, target)
        return
    if link_path.is_symlink() or link_path.is_file():
        link_path.unlink()
    elif link_path.exists():
        raise UnsafeTargetError(f"Refusing to overwrite {link_path}")
    link_path.write_text(render_overlay(root, skill), encoding="utf-8")


def _link_copy(root: Path, dest_root: Path, skill: Skill) -> str:
    skill_dest = dest_root / skill.name
    _ensure_owned_dir(skill_dest)
    if skill_dest.exists():
        shutil.rmtree(skill_dest)
    skill_dest.mkdir(parents=True)

    if skill.is_bundle:
        _copy_tree(skill.source_path, skill_dest)
    else:
        shutil.copyfile(skill.source_path, skill_dest / SKILL_FILE)
    if skill.needs_overlay:
        (skill_dest / SKILL_FILE).write_text(
            render_overlay(root, skill), encoding="utf-8"
        )
    return folder_hash(skill_dest)


def _copy_tree(source_dir: Path, dest_dir: Path) -> None:
    """Replicate ``cp -R <src>/. <dest>/`` (contents, not the dir itself)."""
    for entry in sorted(source_dir.iterdir(), key=lambda p: p.name):
        target = dest_dir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            # copy2, not copyfile: a bundled script must stay executable in the
            # projected view, and folder_hash only digests content, so the
            # preserved mode cannot change a manifest.
            shutil.copy2(entry, target)


def _ensure_owned_dir(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise UnsafeTargetError(f"Refusing to overwrite non-directory {path}")


def _symlink(link_path: Path, target: str) -> None:
    if link_path.is_symlink():
        link_path.unlink()
    elif link_path.is_file():
        # A previously generated overlay file whose skill no longer needs one.
        link_path.unlink()
    elif link_path.exists():
        raise UnsafeTargetError(f"Refusing to overwrite non-symlink {link_path}")
    os.symlink(target, link_path)


def _repo_relative(root: Path, path: Path) -> str:
    """Return ``path`` relative to the repo root as a POSIX string.

    Symlink targets must be repo-relative (e.g. ``.github/skills/foo.md``), not
    absolute, so the links stay valid after clone/move.
    """
    return path.relative_to(root).as_posix()
