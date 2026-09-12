"""Projection-time overlay for skills whose source must stay untouched.

A vendored skill cannot be edited in place — the next sync would overwrite it,
and a silent fork would lose upstream fixes. Yet some of them carry instructions
this repository forbids (auto-committing, merging) or triggers that conflict
with governed routing ("you MUST use this before ANY creative work").

The overlay resolves that without touching the vendor file: when a skill has a
policy or an overridden description, its projected ``SKILL.md`` is *generated*
— the governed frontmatter, a short banner stating what takes precedence, then
the vendor body verbatim. The source file, its hash in ``skills-lock.json`` and
its licence record stay exactly as vendored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ml_python_base.skills_sync.frontmatter import split_frontmatter

if TYPE_CHECKING:
    from pathlib import Path

    from ml_python_base.skills_sync.models import Skill

BANNER_TITLE = "Governed overlay — read first"


def render_overlay(root: Path, skill: Skill) -> str:
    """Return the projected ``SKILL.md`` content for an overlaid skill."""
    source_text = skill.skill_file.read_text(encoding="utf-8")
    front, body = split_frontmatter(source_text)
    source_rel = _source_label(root, skill)

    lines = ["---", f"name: {skill.name}", f"description: {_quote(skill.description)}"]
    for key, value in front.items():
        if key in ("name", "description") or not isinstance(value, str):
            continue
        lines.append(f"{key}: {_quote(value)}")
    lines.append("---")
    lines.append("")
    lines.extend(_banner(skill, source_rel))
    lines.append("")
    lines.append(body.strip("\n"))
    return "\n".join(lines) + "\n"


def _source_label(root: Path, skill: Skill) -> str:
    """How the banner names the governed source file.

    Repo-relative when the source lives under ``root`` (the normal case). When
    a caller projects into a *foreign* root — the harness lab placing a skill in
    a cloned target workspace — the source is elsewhere on disk, so the label
    falls back to the governed path as it reads in the owning repository
    (``.github/skills-external/<name>/SKILL.md``) rather than leaking an
    absolute path or raising.
    """
    try:
        return skill.skill_file.relative_to(root).as_posix()
    except ValueError:
        parts = skill.skill_file.parts
        for anchor in (".github",):
            if anchor in parts:
                return "/".join(parts[parts.index(anchor) :])
        return skill.skill_file.name


def _banner(skill: Skill, source_rel: str) -> list[str]:
    lines = [
        f"> **{BANNER_TITLE}.** Projected by `skills_sync` from `{source_rel}` "
        "(vendored, unmodified). Repository policy takes precedence over any "
        "step below that contradicts it:",
    ]
    for policy in skill.meta.policies:
        lines.append(f"> - **{policy.title}:** {policy.summary}")
    if skill.description != skill.source_description:
        lines.append(
            "> - **Routing:** use this skill only when its governed trigger "
            "applies — " + skill.description
        )
    return lines


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
