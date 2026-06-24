# Automation Policy

This file defines Level 3 enforcement so quality does not depend on model behavior.

## Required Enforcement

- Strict lint and formatting checks.
- CI pipelines for lint/test/security/type-checking.
- Structure validation checks.
- Skill-sync drift gate: generated adapter/skill artifacts must be current.
- PR automation (status checks, optional bots).
- Documentation updates in `docs/` when `src/` or `tests/` change.

## CI Is Read-Only

- CI **verifies**, it never mutates the working tree.
- `make check` is the read-only gate: it first runs `uv sync --locked --exact`
  (the dependency drift guard — see below), then `ruff format --check`,
  `ruff check`, `bandit`, `mypy`, and `pytest` (no auto-formatting, no
  auto-fixing of source).
- `make check-sync` fails if any generated skill artifact or adapter skill
  region is stale relative to the governed sources in `.github/`.
- `make format` and `make fix` are **local-only** — run them before pushing.

## Dependencies And The Drift Guard

A green gate is only meaningful against the **declared** environment. A
dependency `pip`-installed into `.venv` but not added to `pyproject.toml` +
`uv.lock` makes `make check` pass locally yet fail on a clean clone / CI — and a
model's verify loop running in that same `.venv` cannot detect it.

- Every runtime/test dependency MUST be declared in `pyproject.toml` and locked
  with `uv lock`. Never `pip install` / `uv pip install` ad hoc to make a test
  pass — that is hidden, non-reproducible state.
- `make check` runs `uv sync --locked --exact` first: `--locked` fails if
  `pyproject.toml` and `uv.lock` have drifted; `--exact` rebuilds `.venv` to
  exactly the lock, pruning anything undeclared. This mutates only `.venv`,
  never source, so it stays CI-safe.
- "Tests pass" is reportable only after a clean, lock-synced run.

## Baseline Commands

- `make check` — read-only quality gate (use in CI).
- `make check-sync` — skill-sync drift gate (use in CI).
- `make ci` — full read-only pipeline (`check` + `check-sync`).
- `make format` / `make fix` — local-only, mutate the tree.
- `make lint` / `make test` — local helpers (mutating variants).

## Implementation Notes

- Keep enforcement deterministic and reproducible.
- Prefer failing fast in CI for boundary or quality violations.
- Keep local workflow aligned with CI by running `make ci` before pushing.
