# Contributing

Thanks for improving this template. It is the shared harness other projects inherit,
so changes here propagate — small, well-verified changes are worth more than large
ones.

## Setup

```bash
make install       # create .venv from uv.lock and install dependencies
make setup-hooks   # install pre-commit hooks (run once)
make check         # read-only quality gate — should pass on a clean clone
```

Requires Python 3.11+, [uv](https://github.com/astral-sh/uv), and `make`.

## The working loop

The repository documents its own way of working in
[docs/agentic-workflow.md](docs/agentic-workflow.md): **Ground → Plan → Delegate →
Verify → Compound**. Scale the ceremony to the task — a typo needs none, an
architectural change needs an ADR.

## Before you open a pull request

```bash
make format   # apply formatting
make fix      # apply safe lint fixes
make ci       # check + check-sync + check-docs-coverage
```

CI is **read-only**: it verifies and never reformats. If `make ci` is red locally, CI
will be red too.

Three gates catch most review round-trips:

1. **`make check`** — ruff format, ruff lint, bandit, mypy, pytest with coverage.
2. **`make check-sync`** — fails if the generated per-tool skill and agent layouts are
   stale. If you edited anything under `.github/skills/`, `.github/agents/`, or
   `adapters/`, run `make sync-skills` and commit the regenerated files.
3. **`make check-docs-coverage`** — fails if you changed `src/` or `tests/` without
   touching `docs/`. This is deliberate: behaviour changes ship with documentation.

## Conventions

- **English only** in code artifacts — identifiers, docstrings, comments, and docs —
  whatever language the discussion happens in.
- **Absolute imports** inside `src/`.
- **Governed sources are the source of truth.** Edit `.github/skills/` and
  `.github/agents/`, never the generated copies under `.claude/`, `.codex/`,
  `.opencode/`, or `.agents/`.
- **Record durable decisions** as an ADR in `docs/adr/` (`/adr` scaffolds one) and
  non-obvious learnings in `memory/`.

## Adding an external skill

External skills are third-party content redistributed by this repository. Any new one
must declare its origin and licence in the `[external_skill]` table of
`adapters/registry.toml`, or `make check` fails. Add matching attribution to
[NOTICE](NOTICE). If you cannot establish a licence, do not vendor the skill.

## Licence

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
