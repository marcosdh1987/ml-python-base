"""Vendor git behaviour cannot bypass repository governance.

Three layers are checked against the committed repository:

1. every vendored skill that instructs a mutating git action is covered by the
   ``git-actions`` policy in ``adapters/registry.toml``;
2. the projected ``SKILL.md`` of each covered skill carries the policy banner
   while the vendor source stays byte-identical to what the lock records;
3. the Claude Code settings ask before any commit/push/merge command.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ml_python_base.skills_sync.config import load_registry
from ml_python_base.skills_sync.discovery import discover_skills
from ml_python_base.skills_sync.hashing import file_sha256
from ml_python_base.skills_sync.models import KIND_EXTERNAL
from ml_python_base.skills_sync.overlay import BANNER_TITLE
from ml_python_base.skills_sync.permissions import (
    GIT_MUTATING_COMMANDS,
    claude_ask_rules,
    copilot_autoapprove_rules,
    opencode_bash_permission,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = load_registry(REPO_ROOT / "adapters/registry.toml")
POLICY_ID = "git-actions"

# Instructions that would make an agent mutate git history or remotes on its own.
_GIT_MUTATION = re.compile(
    r"\bgit commit\b|\bgit push\b|\bgit merge\b|\bgit rebase\b|\bgit branch -[dD]\b"
    r"|\bgh pr (?:create|merge)\b|\bgit worktree remove\b"
    r"|\bcommit (?:your work|the change|the design|it)\b|\band commit\b",
    re.IGNORECASE,
)


def _policy():
    return next(p for p in REGISTRY.catalog.policies if p.id == POLICY_ID)


def _external_skills():
    return [
        s
        for s in discover_skills(REPO_ROOT, registry=REGISTRY)
        if s.kind == KIND_EXTERNAL
    ]


def _bundle_text(skill) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(skill.source_path.rglob("*.md"))
    )


def test_every_git_mutating_vendored_skill_is_covered_by_the_policy() -> None:
    policy = _policy()
    offenders = sorted(
        s.name
        for s in _external_skills()
        if _GIT_MUTATION.search(_bundle_text(s)) and s.name not in policy.applies_to
    )
    assert offenders == [], (
        f"vendored skills instruct git mutations without the {POLICY_ID} policy: "
        f"{offenders} — add them to [policy.{POLICY_ID}].applies_to"
    )


def test_policy_states_the_governed_rule() -> None:
    summary = _policy().summary
    assert "MUST NOT" in summary
    for token in ("`git commit`", "`git push`", "merge", "delete branches"):
        assert token in summary
    assert "explicitly asks" in summary


@pytest.mark.parametrize("skill_name", sorted(_policy().applies_to))
def test_projected_skill_carries_the_banner_and_source_is_untouched(
    skill_name: str,
) -> None:
    projected = REPO_ROOT / ".claude/skills" / skill_name / "SKILL.md"
    assert projected.is_file() and not projected.is_symlink()
    text = projected.read_text(encoding="utf-8")
    assert BANNER_TITLE in text
    assert _policy().summary in text

    source = REPO_ROOT / ".github/skills-external" / skill_name / "SKILL.md"
    assert BANNER_TITLE not in source.read_text(encoding="utf-8")
    lock = json.loads((REPO_ROOT / "skills-lock.json").read_text(encoding="utf-8"))
    assert lock["skills"][skill_name]["computedHash"] == file_sha256(source)


def test_every_adapter_states_the_policy() -> None:
    for tool in REGISTRY.tools:
        assert tool.adapter_file
        text = (REPO_ROOT / tool.adapter_file).read_text(encoding="utf-8")
        assert _policy().summary in text, f"{tool.adapter_file} lacks the policy"
        assert "NEVER perform git commits" in text, (
            f"{tool.adapter_file} lacks the hand-written git runtime rule"
        )


# --- Tool-level enforcement -----------------------------------------------------
#
# Instruction-level protection (the prose above) is necessary but not sufficient:
# it reaches the model, not the tool call. Where a platform exposes a permission
# primitive, the same rule is projected into it, derived from one list
# (`skills_sync.permissions`) so the two dialects cannot drift.


def test_claude_settings_ask_before_git_mutations() -> None:
    settings = json.loads(
        (REPO_ROOT / ".claude/settings.json").read_text(encoding="utf-8")
    )
    ask = settings.get("permissions", {}).get("ask", [])
    for pattern in claude_ask_rules():
        assert pattern in ask, f"missing ask rule {pattern}"
    assert {"Bash(git commit:*)", "Bash(git push:*)", "Bash(git merge:*)"} <= set(ask)


def test_opencode_config_asks_before_git_mutations() -> None:
    config = json.loads((REPO_ROOT / "opencode.json").read_text(encoding="utf-8"))
    bash = config.get("permission", {}).get("bash")
    assert bash == opencode_bash_permission(), (
        "opencode.json permission.bash must equal the derived governed map"
    )
    # Order is load-bearing: OpenCode applies the LAST matching rule, so the
    # catch-all has to come before the specific asks.
    keys = list(bash)
    assert keys[0] == "*"
    assert all(bash[key] == "ask" for key in keys[1:])


@pytest.mark.parametrize(
    "agent_file", sorted((REPO_ROOT / ".opencode/agents").glob("*.md"))
)
def test_projected_opencode_agents_carry_the_git_permission(agent_file: Path) -> None:
    """An agent that may run shell may not run git's mutating commands unattended."""
    text = agent_file.read_text(encoding="utf-8")
    if "\n  bash: deny\n" in text:
        return  # no shell at all: nothing to restrict
    assert "\n  bash:\n" in text, f"{agent_file.name} does not project a bash map"
    for pattern, decision in opencode_bash_permission().items():
        assert f'    "{pattern}": {decision}' in text, (
            f"{agent_file.name} is missing the {pattern} rule"
        )


def test_copilot_recommended_settings_never_auto_approve_git_mutations() -> None:
    """VS Code auto-approves common git commands by default; these must not be."""
    path = REPO_ROOT / ".vscode/settings.recommended.json"
    assert path.is_file(), "the recommended Copilot settings are not shipped"
    settings = json.loads(path.read_text(encoding="utf-8"))
    assert settings["chat.tools.terminal.autoApprove"] == copilot_autoapprove_rules()
    assert all(
        value is False for value in settings["chat.tools.terminal.autoApprove"].values()
    )


def test_copilot_recommended_settings_are_trackable_but_personal_ones_are_not() -> None:
    """The template ships one file under .vscode/; the rest stays the developer's."""
    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "\n.vscode/*\n" in ignore, "a `.vscode/` rule would block the negation"
    assert "\n!.vscode/settings.recommended.json\n" in ignore


def test_read_only_agents_still_deny_shell_outright() -> None:
    """The permission map must not have widened a read-only agent's access."""
    planner = (REPO_ROOT / ".opencode/agents/planner.md").read_text(encoding="utf-8")
    assert "\n  bash: deny\n" in planner
    assert "git commit" not in planner


def test_every_mutating_command_of_the_policy_is_enforced_somewhere() -> None:
    """The prose names four action classes; each maps to an enforced command."""
    summary = _policy().summary
    commands = " ".join(GIT_MUTATING_COMMANDS)
    for token, expected in (
        ("`git commit`", "git commit"),
        ("`git push`", "git push"),
        ("merge", "git merge"),
        ("delete branches", "git branch -d"),
    ):
        assert token in summary
        assert expected in commands
