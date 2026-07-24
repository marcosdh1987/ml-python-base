# Engineering Standards

This document defines coding and operational standards across tools.

## Language Policy

- User interaction language follows user language.
- Code artifacts are always in English:
  - identifiers
  - docstrings
  - comments
  - generated technical docs

## Python and Environment

- Use Python for generated implementation by default.
- Use `uv` workflows via Makefile commands.
- Do not recommend direct `pip` usage for project dependencies.

## Command Policy

Before suggesting project commands, inspect and prioritize `Makefile` targets.

Primary commands:

- `make install`
- `make add PKG=<package>`
- `make format` / `make fix` — local-only (mutate the tree).
- `make check` — read-only quality gate (CI-safe).
- `make ci` — full read-only pipeline (`check` + `check-sync`).

### Retry and Malformed-Command Policy

The **execution loop** is the agent's working iteration cycle: form hypothesis →
run targeted command → interpret result → update hypothesis or advance.

- Run each verification command once per hypothesis.
- If a command fails, diagnose the failure before re-running it.
- A truncated or malformed command (incomplete syntax, missing arguments) MUST NOT
  be retried as-is; correct the command before retrying. Repeated identical
  malformed retries are a **workflow failure signal** (the agent is thrashing) and
  require the execution loop to pause for diagnosis before continuing.
- Do not repeat read-only inspection commands (file reads, grep, etc.) unless the
  working hypothesis has changed since the last run.

### Bug-Fix Discipline

For any bug fix, follow an explicit, mandatory loop rather than ad hoc reasoning:

1. **Reproduce** the failure with a concrete command or test before editing.
2. **Isolate** the smallest code path that triggers it.
3. **Hypothesize** the root cause and state it plainly, backed by evidence.
4. **Fix** the cause minimally, changing only the files in scope.
5. **Verify** against the same failure mode: re-run the exact repro and the
   narrowest relevant target test.

The `systematic_debugging` skill carries the full loop. Jumping straight to a fix
without a stated repro and hypothesis is a **workflow failure signal**.

## Code Quality

- Enforce type hints whenever practical; `make typecheck` runs `mypy`.
- Prefer `Pydantic` for structured validation/configuration.
- Use Ruff for linting/formatting workflows.
- Run security checks (`bandit`) through `make check`.
- CI is read-only: never rely on CI to format or fix code — do it locally
  before pushing (see `.github/automation.md`).

## Imports

- Use absolute imports only.
- Avoid relative imports (`from .x import y`, `from ..x import y`).

## Prompt Design

For complex LLM prompts, prefer structured XML-like sections:

- `<thinking>`
- `<context>`
- `<instructions>`

## Validation Checklist

Before finalizing generated work:

1. Code artifacts are in English.
2. The narrowest relevant target test for the changed behavior ran and passed
   (focused test first); `make check` covers the broader gate. Syntax or manual
   inspection only supplements executed tests — it never replaces them.
3. Data flow respects raw vs processed boundaries.
4. Implementation changes include/update documentation under `docs/`.

## Branch Finishing

When finishing a branch, keep the work scoped to the task. Do not spend
branch-finishing time on unrelated repository chores — git identity/config,
environment bootstrap, or tooling setup — unless the task itself is specifically
about repository bootstrap. Lateral setup work during branch finishing is a scope
leak and should be deferred or raised separately.
