"""Enumerate governed skills and apply the internal-over-external precedence."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ml_python_base.skills_sync.catalog import apply_registry, meta_from_mapping
from ml_python_base.skills_sync.frontmatter import parse_frontmatter
from ml_python_base.skills_sync.models import KIND_EXTERNAL, KIND_INTERNAL, Skill

if TYPE_CHECKING:
    from ml_python_base.skills_sync.models import Registry

INTERNAL_DIR = Path(".github/skills")
EXTERNAL_DIR = Path(".github/skills-external")
SKILL_FILE = "SKILL.md"
_EXCLUDED_STEMS = frozenset({"README"})


def discover_skills(
    root: Path,
    internal_dir: Path = INTERNAL_DIR,
    external_dir: Path = EXTERNAL_DIR,
    registry: Registry | None = None,
) -> list[Skill]:
    """Return internal skills (sorted) followed by external skills (sorted).

    The ordering matches the legacy shell glob expansion, which is what keeps
    the generated manifest byte-identical. External skills whose name collides
    with an internal skill are dropped (internal precedence).

    Each skill carries the catalog metadata declared in its frontmatter. When a
    ``registry`` is given, its ``[skill.*]`` overlays and ``[policy.*]`` blocks
    are merged on top (see :func:`catalog.apply_registry`).
    """
    internal = _discover_internal(root / internal_dir)
    internal_names = {skill.name for skill in internal}
    external = _discover_external(root / external_dir, internal_names)
    skills = internal + external
    if registry is not None:
        skills = apply_registry(skills, registry)
    return skills


def _discover_internal(internal_path: Path) -> list[Skill]:
    """Enumerate internal skills in either supported shape, sorted by name.

    A flat ``<name>.md`` is a prose-only skill. A ``<name>/`` directory is a
    bundle: ``SKILL.md`` is its entry point and the helper files it runs sit
    beside it. A directory without ``SKILL.md`` is not a skill and is skipped.
    """
    if not internal_path.is_dir():
        return []
    skills: list[Skill] = []
    for path in internal_path.iterdir():
        if path.name.startswith("."):
            continue
        if path.is_dir():
            skill_file = path / SKILL_FILE
            if not skill_file.is_file():
                continue
            name = path.name
        elif path.suffix == ".md" and path.stem not in _EXCLUDED_STEMS:
            skill_file = path
            name = path.stem
        else:
            continue
        skills.append(_build_skill(name, KIND_INTERNAL, path, skill_file))
    skills.sort(key=lambda skill: skill.name)
    return skills


def _discover_external(external_path: Path, internal_names: set[str]) -> list[Skill]:
    if not external_path.is_dir():
        return []
    skills: list[Skill] = []
    for directory in sorted(external_path.iterdir(), key=lambda p: p.name):
        if not directory.is_dir():
            continue
        if directory.name in internal_names:
            continue  # internal precedence
        skill_file = directory / SKILL_FILE
        if not skill_file.is_file():
            continue
        skills.append(
            _build_skill(directory.name, KIND_EXTERNAL, directory, skill_file)
        )
    return skills


def _build_skill(name: str, kind: str, source: Path, skill_file: Path) -> Skill:
    front = _read_frontmatter(skill_file)
    description = " ".join(str(front.get("description", "")).split())
    return Skill(
        name=name,
        kind=kind,
        source_path=source,
        description=description,
        source_description=description,
        meta=meta_from_mapping(front),
    )


def _read_frontmatter(skill_file: Path) -> dict:
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError:
        return {}
    return parse_frontmatter(text)


def _read_description(skill_file: Path) -> str:
    """Extract the ``description:`` value from the YAML frontmatter, if present."""
    return " ".join(str(_read_frontmatter(skill_file).get("description", "")).split())
