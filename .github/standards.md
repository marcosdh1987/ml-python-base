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

Two gates apply to every fix:

- Every edit batch must pass a fast parse/compile check (`py_compile` / `make lint`)
  before any smoke test; building on a file that does not parse is a
  **workflow failure signal**.
- If the preferred test runner is unavailable, fall back immediately to the lightest
  check that executes the code; stopping, or verifying with a syntax check alone, is
  a **workflow failure signal**.

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

## Release Discipline

Releases of this template are guarded and traceable. The tooling
(`scripts/harness_release.py`, `make/harness.mk`) is read-only by default; git
mutation happens ONLY inside two guarded commands — `make release-pr` and
`make publish-release` — each of which requires its full guard set (including the
release preflight) to pass and then an explicit interactive confirmation. Full
policy: `docs/harness-release-lifecycle.md`.

**The tag is the last step, never the first.** The mandatory order is:

1. `make new-version` — derives the version from the classified changes since the
   latest tag and reconciles `pyproject.toml` + `CHANGELOG.md`. Never invent the
   number. Curate the scaffolded CHANGELOG bullets by hand.
2. `make release-pr` — commits exactly the bump files, pushes, and opens the
   release PR (after confirmation). Merge it to `main`.
3. `make publish-release` — on `main`: green preflight, confirmation, then tag,
   push, GitHub Release, and manifest. The tag is created only after everything
   else has passed.

Rules an agent MUST follow:

- Never create or push a tag outside `make publish-release` while its preflight is
  red. `make harness-release` remains the manual fallback: it **prints** the
  publish commands — printing is not executing.
- The confirmation prompt is the human gate. An agent must never answer it, pass
  `YES=1`, or pipe input into it on its own; the operator confirms.
- A published tag is immutable. Never `git tag -f`, never `git push --force` a tag,
  never delete a tag that already has a GitHub Release or a downstream consumer.
- Never edit `pyproject.toml` or `CHANGELOG.md` to match a tag that already exists.
  That inverts the source of truth: the files define the version, the tag records it.
- Preflight failures are preconditions, not obstacles to bypass. Do not reach for
  `SKIP_GATES=1` to make a red preflight green; it skips `make check` only, and the
  precondition problems remain.
- `pyproject.toml` and `uv.lock` are platform paths. When the platform delta since
  the base tag is **exactly** that pair, the preflight auto-allows it (that pair is
  the version bump itself). Any other platform path still fails the preflight and
  needs its own reviewed PR with a migration note — `ALLOW_PLATFORM=1` exists for
  that reviewed case only, never to silence the check.

Recovering from a tag created too early — a tag whose commit does not carry the
matching `pyproject.toml` version — depends on whether it was published:

- **No GitHub Release, no downstream consumer**: the tag is untracked noise. Delete
  it locally and on the remote (`git tag -d vX.Y.Z` and
  `git push origin :refs/tags/vX.Y.Z`), then restart the order above. Deleting a
  remote tag is outward-facing: confirm with the maintainer before running it.
- **Already published or consumed**: leave it. Reconcile the files to the next
  version and release that instead.

## Branch Finishing

When finishing a branch, keep the work scoped to the task. Do not spend
branch-finishing time on unrelated repository chores — git identity/config,
environment bootstrap, or tooling setup — unless the task itself is specifically
about repository bootstrap. Lateral setup work during branch finishing is a scope
leak and should be deferred or raised separately.
