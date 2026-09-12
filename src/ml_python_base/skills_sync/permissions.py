"""The machine-readable half of the ``git-actions`` policy.

The policy itself is prose declared once in ``adapters/registry.toml`` and
rendered into every adapter file and into the projected ``SKILL.md`` of each
vendored skill it covers. Prose reaches the model; it does not stop a tool call.

This module carries the same rule as **commands**, so the tools that expose a
permission primitive can enforce it mechanically:

* **Claude Code** — ``permissions.ask`` entries in ``.claude/settings.json``.
* **OpenCode** — a ``permission.bash`` glob map, globally in ``opencode.json``
  and per agent in the generated ``.opencode/agents/<name>.md`` frontmatter.
* **GitHub Copilot (VS Code)** — ``chat.tools.terminal.autoApprove`` rules, which
  the template can only *offer*: workspace settings are gitignored, so the rules
  ship as ``.vscode/settings.recommended.json`` for a developer to adopt.

Every dialect is derived from one list so they cannot drift;
``tests/skills_sync/test_policies.py`` asserts the derivation against what is
actually committed.

``ask``, never ``deny``: the policy allows the user to authorize a specific
action in the session, and ``deny`` would refuse even then.
"""

from __future__ import annotations

ASK = "ask"
ALLOW = "allow"

#: Command prefixes that must reach a human before they run. Mutating history or
#: a remote, in the two CLIs the harness drives (``git`` and ``gh``). Ordered
#: most-common-first; the derivations below preserve this order.
GIT_MUTATING_COMMANDS: tuple[str, ...] = (
    "git commit",
    "git push",
    "git merge",
    "git rebase",
    "git branch -d",
    "git branch -D",
    "gh pr merge",
)


def claude_ask_rules() -> tuple[str, ...]:
    """The ``permissions.ask`` entries Claude Code expects."""
    return tuple(f"Bash({command}:*)" for command in GIT_MUTATING_COMMANDS)


def copilot_autoapprove_rules() -> dict[str, bool]:
    """The ``chat.tools.terminal.autoApprove`` rules VS Code expects.

    ``False`` means "never auto-approve", i.e. the command reaches the developer
    for confirmation. Recent VS Code auto-approves common ``git`` commands by
    default, so stating these explicitly is what keeps a commit or a push from
    running unattended in agent mode. Regular expressions (slash-wrapped) are
    anchored so only the command itself matches, not a mention of it.
    """
    return {f"/^{_escape(command)}\\b/": False for command in GIT_MUTATING_COMMANDS}


def _escape(command: str) -> str:
    """Escape a command prefix for use inside a VS Code autoApprove regex."""
    return command.replace("-", "\\-")


def opencode_bash_permission() -> dict[str, str]:
    """The ``permission.bash`` map OpenCode expects.

    ``*: allow`` first, then one ``ask`` per mutating command: OpenCode applies
    the **last** matching rule, so the specific entries must follow the
    catch-all. Insertion order is therefore load-bearing — keep it when
    rendering.
    """
    return {"*": ALLOW, **{f"{command}*": ASK for command in GIT_MUTATING_COMMANDS}}
