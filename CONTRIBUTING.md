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

## Adding an internal skill

An internal skill takes either shape, both under `.github/skills/`:

- **prose only** — a single `<name>.md`;
- **prose plus files it runs** — a `<name>/` folder with `SKILL.md` as its entry
  point and the scripts, templates or references beside it.

Give it YAML frontmatter with `name` (matching the file or folder name), a
`description` written as a trigger, a `summary` under 140 characters, and the
catalog metadata (`family`, `visibility` — `internal` unless it is a genuine
developer entrypoint — `profile`, `risk`, `triggers`). Add a routing scenario to
`tests/routing/scenarios.toml`, then run `make sync-skills` and commit the
regenerated views and `docs/generated/skills-catalog.md`. When the skill invokes a
bundled script, tell the agent to call the governed path
(`.github/skills/<name>/<script>`), never a native copy. Details in
[.github/skills/README.md](.github/skills/README.md) and
[docs/skills-guide.md](docs/skills-guide.md).

## Retiring a skill

Set `visibility: legacy` plus `replacement: <live skill>` in its frontmatter, or
delete it and add `[alias.<old>] replacement = "<live skill>"` to
`adapters/registry.toml`. Either way the old name keeps resolving and stops
competing in discovery; `make check` refuses a replacement that is not live.

## Adding an external skill

External skills are third-party content redistributed by this repository. Any new one
must declare its origin and licence in the `[external_skill]` table of
`adapters/registry.toml`, or `make check` fails. Add matching attribution to
[NOTICE](NOTICE), a `[skill.<name>]` overlay for its catalog metadata, and — if its
body instructs commits, pushes or merges — list it under `[policy.git-actions]`
(`make check` fails otherwise). Never edit the vendored file; the overlay is
projected over it. If you cannot establish a licence, do not vendor the skill.

## Licence

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
