"""Every legacy name, proved one property at a time.

The rule this file enforces: **a legacy alias must not compete in model
discovery, and must still resolve for a migrating caller.** Each test below is
one column of the alias table in ``docs/skills-catalog-v3-audit.md``, so the
documented claim and the enforced behaviour cannot drift.

An alias exists only while something still says the old name — an old prompt, a
downstream repository, a saved benchmark case. Removing one is a deliberate
breaking change, which is why the table records *why* each is still here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml_python_base.skills_sync.catalog import build_view, resolve_name
from ml_python_base.skills_sync.config import load_registry
from ml_python_base.skills_sync.discovery import discover_skills
from ml_python_base.skills_sync.renderer import BEGIN_MARKER, END_MARKER
from ml_python_base.skills_sync.routing import route

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = load_registry(REPO_ROOT / "adapters/registry.toml")
SKILLS = discover_skills(REPO_ROOT, registry=REGISTRY)
VIEW = build_view(SKILLS, REGISTRY)
ALIASES = VIEW.aliases
ALIAS_IDS = [alias.name for alias in ALIASES]

#: Native views an alias must never appear in.
NATIVE_DIRS = (".claude/skills", ".codex/skills", ".opencode/skills", ".agents/skills")


def test_the_catalog_declares_exactly_the_documented_aliases() -> None:
    assert ALIAS_IDS == [
        "create_repository_interface",
        "create_use_case",
        "execute_engineering_task",
        "source-command-retro",
        "source-command-verify",
    ]


@pytest.mark.parametrize("alias", ALIASES, ids=ALIAS_IDS)
def test_alias_resolves_to_a_live_canonical_skill(alias) -> None:
    """Column: *canonical destination*."""
    live = {s.name: s for s in SKILLS if not s.meta.is_legacy}
    assert alias.replacement in live, f"{alias.name} points at a dead skill"
    assert resolve_name(alias.name, SKILLS, REGISTRY) == alias.replacement


@pytest.mark.parametrize("alias", ALIASES, ids=ALIAS_IDS)
def test_alias_is_not_projected_into_any_native_view(alias) -> None:
    """Column: *projected?* — must be **no**, in every tool."""
    for native in NATIVE_DIRS:
        assert not (REPO_ROOT / native / alias.name).exists(), (
            f"{alias.name} is materialized in {native}: it would be discoverable"
        )


@pytest.mark.parametrize("alias", ALIASES, ids=ALIAS_IDS)
def test_alias_has_no_governed_source_file(alias) -> None:
    """A name kept only as metadata: no skill file backs it any more."""
    assert not (REPO_ROOT / ".github/skills" / f"{alias.name}.md").exists()
    assert not (REPO_ROOT / ".github/skills" / alias.name).exists()
    assert not (REPO_ROOT / ".github/skills-external" / alias.name).exists()


@pytest.mark.parametrize("alias", ALIASES, ids=ALIAS_IDS)
def test_alias_cannot_auto_trigger(alias) -> None:
    """Column: *can auto-trigger?* — must be **no**.

    Auto-triggering needs a skill the model can pick from its own description.
    An alias has no skill, no description and no trigger of its own; it appears
    in the adapter only inside the one-line "legacy names" mapping.
    """
    assert alias.name not in {s.name for s in SKILLS}
    assert alias.name not in {s.name for s in VIEW.discoverable}
    for skill in SKILLS:
        assert alias.name not in skill.meta.triggers


@pytest.mark.parametrize("alias", ALIASES, ids=ALIAS_IDS)
def test_alias_is_available_for_migration(alias) -> None:
    """Column: *available for migration?* — must be **yes**.

    A caller that still says the old name is routed to the replacement rather
    than told the skill does not exist.
    """
    decision = route(f"please run {alias.name} on this repo", SKILLS, REGISTRY)
    assert decision.skill == alias.replacement
    assert decision.resolved_from == alias.name


@pytest.mark.parametrize("alias", ALIASES, ids=ALIAS_IDS)
def test_alias_appears_in_every_adapter_only_as_a_mapping(alias) -> None:
    """Discoverable enough to migrate, never listed as a choice."""
    for tool in REGISTRY.tools:
        assert tool.adapter_file
        text = (REPO_ROOT / tool.adapter_file).read_text(encoding="utf-8")
        block = text.split(BEGIN_MARKER)[1].split(END_MARKER)[0]
        assert f"`{alias.name}` → `{alias.replacement}`" in block, (
            f"{tool.adapter_file} does not map {alias.name}"
        )
        listings = block.split("**Legacy names**")[0]
        assert f"`{alias.name}`" not in listings, (
            f"{alias.name} is listed as a usable skill in {tool.adapter_file}"
        )


@pytest.mark.parametrize("alias", ALIASES, ids=ALIAS_IDS)
def test_alias_carries_a_reason_to_still_exist(alias) -> None:
    """An alias without a recorded reason is one nobody can ever retire."""
    assert alias.note.strip(), f"{alias.name} has no note explaining why it remains"


def test_retired_first_party_skills_left_no_provenance_behind() -> None:
    """The two removed skills are gone from the lock and from NOTICE."""
    lock = json.loads((REPO_ROOT / "skills-lock.json").read_text(encoding="utf-8"))
    notice = (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
    for name in ("source-command-retro", "source-command-verify"):
        assert name not in lock["skills"]
        assert f"`.github/skills-external/{name}/`" not in notice
