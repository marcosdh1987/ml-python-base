"""Deterministic skill-routing evals (run in CI; no model involved).

The scenarios in ``scenarios.toml`` are the contract. They are checked against
the reference router built from the catalog metadata, and a few structural
invariants guard the catalog itself: every entrypoint is exercised, routing
rules only name live skills, legacy names always resolve, and the small-model
path lands on skills that actually carry one.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from ml_python_base.skills_sync.catalog import build_view, resolve_name
from ml_python_base.skills_sync.config import load_registry
from ml_python_base.skills_sync.discovery import discover_skills
from ml_python_base.skills_sync.models import VISIBILITY_DEVELOPER
from ml_python_base.skills_sync.routing import MODE_LOCAL_MODEL, route

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_PATH = Path(__file__).with_name("scenarios.toml")
REQUIRED_TAGS = {
    "positive",
    "negative",
    "overlap",
    "legacy",
    "small-model",
    "specialist",
    "hidden",
}

REGISTRY = load_registry(REPO_ROOT / "adapters/registry.toml")
SKILLS = discover_skills(REPO_ROOT, registry=REGISTRY)
VIEW = build_view(SKILLS, REGISTRY)


def load_scenarios() -> list[dict]:
    data = tomllib.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    scenarios = data["scenario"]
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids)), "duplicate scenario ids"
    return scenarios


SCENARIOS = load_scenarios()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario_routes_as_expected(scenario: dict) -> None:
    decision = route(scenario["prompt"], SKILLS, REGISTRY)
    expected = scenario["expected_skills"]
    context = f"{scenario['id']}: {decision.as_dict()}"

    if scenario.get("expect_none"):
        assert decision.skill is None, context
    else:
        assert decision.skill in expected, context
        assert decision.family == scenario["expected_family"], context
    assert decision.skill not in scenario["forbidden_skills"], context
    if "expected_mode" in scenario:
        assert decision.mode == scenario["expected_mode"], context
    if not scenario.get("ambiguous_ok"):
        assert not decision.ambiguous, f"tie at the top — {context}"


def test_suite_covers_every_required_tag() -> None:
    seen = {tag for s in SCENARIOS for tag in s["tags"]}
    assert seen >= REQUIRED_TAGS, f"missing tags: {sorted(REQUIRED_TAGS - seen)}"


def test_every_entrypoint_is_exercised_by_a_scenario() -> None:
    expected = {name for s in SCENARIOS for name in s["expected_skills"]}
    missing = sorted(s.name for s in VIEW.entrypoints if s.name not in expected)
    assert missing == [], f"entrypoints without a routing scenario: {missing}"


def test_scenario_names_only_known_skills_or_aliases() -> None:
    known = {s.name for s in SKILLS} | {a.name for a in REGISTRY.catalog.aliases}
    for scenario in SCENARIOS:
        for name in scenario["expected_skills"] + scenario["forbidden_skills"]:
            assert name in known, f"{scenario['id']} names unknown skill {name}"


def test_intents_point_at_developer_entrypoints() -> None:
    by_name = {s.name: s for s in SKILLS}
    for intent in REGISTRY.catalog.intents:
        assert by_name[intent.skill].meta.visibility == VISIBILITY_DEVELOPER, (
            f"intent '{intent.want}' → {intent.skill} is not a developer entrypoint"
        )


def test_routing_rules_name_only_live_skills() -> None:
    live = {s.name for s in SKILLS if not s.meta.is_legacy}
    for rule in REGISTRY.catalog.routing_rules:
        for name in re.findall(r"`([a-z0-9_-]+)`", rule):
            if name.startswith("mode:") or name in {"mode"}:
                continue
            if "_" in name or "-" in name:
                assert name in live, f"routing rule names non-live skill `{name}`"


def test_every_legacy_name_resolves_to_a_live_entry() -> None:
    live = {s.name for s in SKILLS if not s.meta.is_legacy}
    for alias in VIEW.aliases:
        assert resolve_name(alias.name, SKILLS, REGISTRY) in live
        decision = route(f"use {alias.name} here", SKILLS, REGISTRY)
        assert decision.skill == alias.replacement
        assert decision.resolved_from == alias.name


def test_small_model_scenarios_land_on_skills_with_a_small_model_path() -> None:
    by_name = {s.name: s for s in SKILLS}
    for scenario in SCENARIOS:
        if "small-model" not in scenario["tags"]:
            continue
        decision = route(scenario["prompt"], SKILLS, REGISTRY)
        assert decision.mode == MODE_LOCAL_MODEL, scenario["id"]
        assert decision.skill is not None
        assert by_name[decision.skill].meta.small_model_path, scenario["id"]


def test_developer_catalog_is_materially_smaller_than_the_flat_list() -> None:
    """The definition of done: fewer names to know, no capability removed."""
    discoverable = len(VIEW.discoverable)
    assert len(VIEW.entrypoints) <= 9
    assert len(VIEW.entrypoints) * 2 <= discoverable
    assert discoverable + len(VIEW.hidden) >= 25  # nothing materially removed
