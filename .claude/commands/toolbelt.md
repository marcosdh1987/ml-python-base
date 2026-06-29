---
description: Inspect available MCP, CLI, Make, and service tools for the current task.
argument-hint: <task or question to equip>
allowed-tools: Read, Grep, Glob, Bash(make toolbelt-doctor:*), Bash(git status:*), Bash(git remote:*), Bash(command -v:*), Bash(gh:*), Bash(docker:*), Bash(uv:*), Bash(curl:*)
---

Equip the current task with the repository toolbelt: **$ARGUMENTS**

Steps:

1. Read `docs/claude-toolbelt.md`, `.mcp.json`, and the relevant Makefile targets.
2. Run `make toolbelt-doctor` when local CLI/service availability matters.
3. Identify which available MCP server, CLI, Make target, or local service should
   answer the task before asking the user.
4. For GitHub work, prefer `gh` or a configured GitHub MCP server. For dependency
   docs, prefer `context7`. For local runtime state, prefer Make targets, `docker`,
   and bounded `curl` checks.
5. Ask the user only for information that cannot be retrieved through configured
   tools or that requires a product decision.

Reference: `docs/claude-toolbelt.md`.
