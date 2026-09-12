"""Tests for catalog metadata: merge precedence, validation, views, aliases."""

from __future__ import annotations

from pathlib import Path

import pytest

from ml_python_base.skills_sync.catalog import (
    apply_registry,
    assert_valid_catalog,
    build_view,
    catalog_warnings,
    meta_from_mapping,
    resolve_name,
    validate_catalog,
)
from ml_python_base.skills_sync.config import load_registry
from ml_python_base.skills_sync.discovery import discover_skills
from ml_python_base.skills_sync.errors import RegistryError
from ml_python_base.skills_sync.models import (
    VISIBILITY_DEVELOPER,
    VISIBILITY_LEGACY,
    Alias,
    CatalogSpec,
    Governance,
    Intent,
    Policy,
    Registry,
    Skill,
    SkillMeta,
    short_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _registry(catalog: CatalogSpec | None = None) -> Registry:
    return Registry(
        schema_version=1,
        governance=Governance(files=(), automation="", orchestration=""),
        tools=(),
        catalog=catalog or CatalogSpec(),
    )


def _skill(name: str, **meta: object) -> Skill:
    return Skill(
        name=name,
        kind="internal",
        source_path=Path(f".github/skills/{name}.md"),
        description=f"Use when {name}.",
        source_description=f"Use when {name}.",
        meta=SkillMeta(**meta),  # type: ignore[arg-type]
    )


# --- merge precedence -----------------------------------------------------------


def test_meta_from_mapping_reads_every_declared_key() -> None:
    meta = meta_from_mapping(
        {
            "family": "ideation",
            "visibility": "developer",
            "profile": "core",
            "auto_trigger": "false",
            "maturity": "experimental",
            "risk": "read-only",
            "small_model_path": True,
            "triggers": ["a", "b c"],
            "replacement": "",
            "summary": "  short   text ",
        }
    )
    assert meta.family == "ideation"
    assert meta.visibility == "developer"
    assert meta.auto_trigger is False
    assert meta.maturity == "experimental"
    assert meta.risk == "read-only"
    assert meta.small_model_path is True
    assert meta.triggers == ("a", "b c")
    assert meta.summary == "short text"


def test_registry_overlay_wins_field_by_field_and_overrides_description() -> None:
    skill = _skill("vendored", family="unclassified", visibility="internal")
    registry = _registry(
        CatalogSpec(
            overlays={
                "vendored": {
                    "visibility": "developer",
                    "description": "Governed trigger.",
                }
            },
            policies=(
                Policy(id="p", title="P", summary="S", applies_to=("vendored",)),
            ),
        )
    )
    (merged,) = apply_registry([skill], registry)
    assert merged.meta.visibility == "developer"
    assert merged.meta.family == "unclassified"  # untouched by the overlay
    assert merged.description == "Governed trigger."
    assert merged.source_description == "Use when vendored."
    assert [p.id for p in merged.meta.policies] == ["p"]
    assert merged.needs_overlay


def test_alias_that_shadows_a_present_skill_retires_it() -> None:
    """Governance sync overlays files; a retired directory left behind must not
    resurrect the skill or break validation."""
    skills = [_skill("verify_changes", visibility="developer"), _skill("old_verify")]
    registry = _registry(
        CatalogSpec(aliases=(Alias(name="old_verify", replacement="verify_changes"),))
    )
    merged = {s.name: s for s in apply_registry(skills, registry)}
    assert merged["old_verify"].meta.is_legacy
    assert merged["old_verify"].meta.replacement == "verify_changes"
    assert validate_catalog(list(merged.values()), registry) == []
    view = build_view(list(merged.values()), registry)
    assert [a.name for a in view.aliases] == ["old_verify"]  # listed once


def test_skill_without_overlay_or_policy_needs_no_overlay() -> None:
    (merged,) = apply_registry([_skill("plain")], _registry())
    assert not merged.needs_overlay


# --- validation -----------------------------------------------------------------


def test_validate_flags_every_inconsistency() -> None:
    skills = [
        _skill("live", visibility="developer", family="ideation"),
        _skill("old", visibility="legacy"),  # no replacement
        _skill("odd", visibility="mystery", risk="nope", maturity="deprecated"),
        _skill("stray", family="not-a-family"),
        _skill("secret", visibility="hidden", family="ideation"),
    ]
    registry = _registry(
        CatalogSpec(
            families=("ideation",),
            overlays={"ghost": {"visibility": "internal", "bogus": 1}},
            aliases=(
                Alias(name="live", replacement="live"),
                Alias(name="gone", replacement="old"),
            ),
            policies=(Policy(id="p", title="P", summary="S", applies_to=("nope",)),),
            intents=(Intent(want="x", skill="secret"), Intent(want="y", skill="zzz")),
        )
    )
    problems = "\n".join(validate_catalog(skills, registry))
    warnings = "\n".join(catalog_warnings(skills, registry))
    assert "[skill.ghost] overlays a skill that is not present" in warnings
    assert "[policy.p] applies to absent skill 'nope'" in warnings
    assert "intent 'y' points at absent skill 'zzz'" in warnings
    assert "unknown keys: bogus" in problems
    assert "legacy skill needs a live 'replacement'" in problems
    assert "invalid visibility 'mystery'" in problems
    assert "invalid risk 'nope'" in problems
    assert "deprecated skills must have visibility 'legacy'" in problems
    assert "family 'not-a-family' not in [catalog].families" in problems
    assert "family 'unclassified'" not in problems  # the default always passes
    assert "[alias.live] shadows a skill still on disk" in warnings
    assert "[alias.gone] replacement 'old' is legacy" in problems
    assert "non-discoverable skill 'secret'" in problems
    with pytest.raises(RegistryError, match="inconsistent"):
        assert_valid_catalog(skills, registry)


def test_repository_catalog_is_valid() -> None:
    """The committed skills + registry must validate — this is the real gate."""
    registry = load_registry(REPO_ROOT / "adapters/registry.toml")
    skills = discover_skills(REPO_ROOT, registry=registry)
    assert validate_catalog(skills, registry) == []
    assert catalog_warnings(skills, registry) == []


def test_repository_skills_all_declare_a_family() -> None:
    registry = load_registry(REPO_ROOT / "adapters/registry.toml")
    skills = discover_skills(REPO_ROOT, registry=registry)
    unclassified = sorted(s.name for s in skills if s.meta.family == "unclassified")
    assert unclassified == [], f"skills without a family: {unclassified}"


# --- views and aliases ---------------------------------------------------------------


def test_build_view_partitions_by_visibility_and_lists_aliases() -> None:
    skills = [
        _skill("entry", visibility="developer", family="ideation"),
        _skill("prim", visibility="internal", family="ideation", small_model_path=True),
        _skill("opt", visibility="optional", profile="frontend"),
        _skill("ghost", visibility="hidden"),
        _skill("old", visibility=VISIBILITY_LEGACY, replacement="entry"),
    ]
    registry = _registry(
        CatalogSpec(aliases=(Alias(name="older", replacement="prim"),))
    )
    view = build_view(skills, registry)
    assert [s.name for s in view.entrypoints] == ["entry"]
    assert [s.name for s in view.primitives] == ["prim"]
    assert [s.name for s in view.optional] == ["opt"]
    assert [s.name for s in view.hidden] == ["ghost"]
    assert [s.name for s in view.legacy] == ["old"]
    assert [(a.name, a.replacement) for a in view.aliases] == [
        ("old", "entry"),
        ("older", "prim"),
    ]
    assert [s.name for s in view.small_model] == ["prim"]
    assert dict(view.families)["ideation"] == (skills[0], skills[1])
    assert "old" not in {s.name for group in view.families for s in group[1]}


def test_resolve_name_follows_alias_and_legacy_chains() -> None:
    skills = [
        _skill("new", visibility=VISIBILITY_DEVELOPER),
        _skill("mid", visibility=VISIBILITY_LEGACY, replacement="new"),
    ]
    registry = _registry(
        CatalogSpec(aliases=(Alias(name="oldest", replacement="mid"),))
    )
    assert resolve_name("oldest", skills, registry) == "new"
    assert resolve_name("mid", skills, registry) == "new"
    assert resolve_name("new", skills, registry) == "new"
    assert resolve_name("unknown", skills, registry) == "unknown"


def test_short_summary_is_deterministic_and_bounded() -> None:
    long = (
        "Use when diagnosing a bug, failing test, or unexpected behavior — drive a "
        "methodical loop instead of guessing. Prevents thrashing."
    )
    summary = short_summary(long)
    assert summary.startswith("Use when diagnosing a bug")
    assert len(summary) <= 140
    assert short_summary("Short one.") == "Short one."
    assert short_summary("") == ""
