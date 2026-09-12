"""Tests for the dependency-free frontmatter reader."""

from __future__ import annotations

from ml_python_base.skills_sync.frontmatter import (
    as_bool,
    as_str_tuple,
    parse_frontmatter,
    split_frontmatter,
)

SAMPLE = """---
name: demo
description: "Use when: something, with a comma — and a dash."
family: quality-testing-debugging
auto_trigger: false
small_model_path: yes
triggers: [failing test, "keyerror, or worse", 'crash']
policies:
  - git-actions
  - "other-policy"
# a comment line
---

# Body

Text after the fence.
"""


def test_split_returns_mapping_and_body() -> None:
    front, body = split_frontmatter(SAMPLE)
    assert front["name"] == "demo"
    assert front["description"] == "Use when: something, with a comma — and a dash."
    assert body.startswith("\n# Body")
    assert "Text after the fence." in body


def test_scalars_booleans_and_lists() -> None:
    front = parse_frontmatter(SAMPLE)
    assert front["auto_trigger"] is False
    assert front["small_model_path"] is True
    assert front["triggers"] == ["failing test", "keyerror, or worse", "crash"]
    assert front["policies"] == ["git-actions", "other-policy"]


def test_no_fence_yields_empty_mapping() -> None:
    front, body = split_frontmatter("# Just a body\n")
    assert front == {}
    assert body == "# Just a body\n"


def test_unterminated_fence_is_not_frontmatter() -> None:
    front, body = split_frontmatter("---\nname: x\nno closing fence\n")
    assert front == {}
    assert body.startswith("---")


def test_helpers_coerce_loosely_typed_values() -> None:
    assert as_bool("true", False) is True
    assert as_bool("no", True) is False
    assert as_bool("maybe", True) is True
    assert as_str_tuple("a, b ,, c") == ("a", "b", "c")
    assert as_str_tuple(["x", " y "]) == ("x", "y")
    assert as_str_tuple(None) == ()
