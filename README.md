# Python ML Base Project

A Python project template for machine learning and data science work, built around an
**AI harness**: the rules, skills, and quality gates that make coding agents behave
consistently are committed to the repository itself.

## What this repository actually ships

It is a **template**, not an application — there is no service to start and no model to
serve. Cloning it gives you:

1. **A governed AI harness.** Architecture rules, coding standards, operational skills,
   and agent definitions live in `.github/` and are projected into the native format of
   Claude Code, Codex, OpenCode, Antigravity, and GitHub Copilot — so every assistant
   reads the same rules on first load, with no manual prompting.
2. **A skills-projection engine** (`src/ml_python_base/skills_sync`, run via
   `make sync-skills`) that generates those per-tool layouts from one governed source and
   fails CI when they drift.
3. **A Python baseline** — `uv` for dependencies, ruff, mypy, bandit, pytest, pre-commit,
   and a dev container — wired into a single read-only gate: `make check`.

Run `make init NAME=my_project` to turn a fresh clone into your own project, then
`make install` and `make check`.

## 🚀 Features

- **Modern Python 3.11** setup with `uv` for ultra-fast dependency management
- **Reproducible Environments** using `uv.lock`
- **Ruff** for ultra-fast linting and formatting (replaces Black, Flake8, isort, pyupgrade)
- **Jupyter Notebooks** support with automated cleanup (`nbstripout`)
- **Pre-commit hooks** to ensure quality before committing
- **Makefile** commands for common development tasks
- **Testing** setup with pytest and coverage
- **Dev Containers** ready for consistent development environments
- **Claude Toolbelt** guidance for MCP servers, CLIs, and local service checks

## 📋 Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Make
- **Optional**: Docker Desktop & VS Code Dev Containers extension

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

## 🛠️ Quick Start

### 0. Start a New Project from This Template

If this is a fresh clone meant to become a new project, bootstrap it first:

```bash
make init NAME=my_project
```

This renames the `ml_python_base` package, rewrites references (keeping the
upstream template URL so `make template-sync-*` keeps working), creates `.env`
from `.env.example`, installs the environment, refreshes the AI skill/agent
adapters, and runs the read-only quality gates. Preview without writing:
`python3 scripts/init_project.py --name my_project --dry-run`. Details in
[docs/project-init.md](docs/project-init.md); AI assistants can drive the same
flow via the `bootstrap_project` skill.

Planning to develop against a **self-hosted model on your own Mac** instead of burning
cloud tokens? Set that up once with
[docs/local-model-mac-setup.md](docs/local-model-mac-setup.md).

### 1. Setup Development Environment

This command will install the specific Python version defined in the Makefile, create the virtual environment, and sync all dependencies from `uv.lock`.

```bash
# Setup project
make install

# Activate virtual environment
source .venv/bin/activate
```

### 2. Setup Git Hooks (Recommended)

Install pre-commit hooks to automatically clean notebooks and format code before every commit.

```bash
make setup-hooks
```

### 3. Jupyter Notebooks

After running `make install`, a kernel named "Python (uv)" will be automatically registered.

```bash
# Start Jupyter
uv run jupyter lab
```

## 🐳 Dev Containers (Recommended)

This project is configured to run inside a **Dev Container**. This guarantees that you are working in the exact same environment as production (Linux), regardless of your local OS (macOS, Windows).

### How to use

1. Install **Docker Desktop**.
2. Install the **Dev Containers** extension in VS Code.
3. Open the project in VS Code.
4. Click on the pop-up **"Reopen in Container"** (or run the command from the Palette).

### Benefits

- **Zero Setup**: The container installs Python, `uv`, and all dependencies automatically.
- **Production Parity**: Develop on Linux, deploy on Linux.
- **Jupyter Integration**: Notebooks run seamlessly inside the container, using the container's kernel.

## 📦 Managing Dependencies

We use `uv` to manage dependencies in `pyproject.toml` and lock them in `uv.lock`.

### Add a new library

Instead of editing files manually, use the helper command:

```bash
# Add a package (e.g., tensorflow)
make add PKG=tensorflow

# Add a development dependency
make add PKG="pytest --dev"
```

This will:
1. Add the package to `pyproject.toml`
2. Update `uv.lock`
3. Install the package in your environment

### Remove a library

To remove a package you no longer need:

```bash
make remove PKG=tensorflow
```

### Generate requirements.txt

If you need a `requirements.txt` for legacy systems or deployment:

```bash
make generate-requirements
```

## 🎯 Code Quality

The project provides four levels of code quality checks (plus the read-only gate below):

1. **`make fix` (Recommended)**: The "do it all" command. It auto-formats code, sorts imports, removes unused imports, fixes linting issues, and cleans Jupyter notebooks. Run this frequently!
2. **`make fix-force`**: Same as `fix`, but applies "unsafe" fixes. Use with caution (e.g., it might remove imports used only in `try/except` blocks).
3. **`make lint`**: Runs strict static analysis and security checks (Bandit). It does not modify files. Use this to verify your code before pushing.
4. **`make format`**: A lighter version of `fix`. Only formats code and sorts imports.

```bash
# 1. Clean everything (Safe mode)
make fix

# 2. Clean everything (Aggressive mode - check changes after!)
make fix-force

# 3. Verify quality and security (Read-only check)
make lint

# 4. Read-only gate: format check + lint + bandit + mypy + tests
make check

# 5. Full CI pipeline — read-only, never mutates the tree
#    (= make check + make check-sync + make check-docs-coverage)
make ci
```

CI **verifies and never fixes**: run `make fix` / `make format` locally before
pushing. A green `make ci` locally means a green CI.

## 📁 Project Structure

```
.
├── src/                    # Source code
├── tests/                  # Test files
├── notebooks/              # Jupyter notebooks
├── memory/                 # Persistent project memory (context, learnings, patterns)
├── docs/                   # Documentation, including:
│   └── adr/                #   Architecture Decision Records (the durable "why")
├── .github/                # Governed source of truth for the harness:
│   ├── skills/             #   internal skills (+ skills-external/ for vendored)
│   └── agents/             #   tool-agnostic agent definitions
├── adapters/               # registry.toml (tools + skills catalog) + Jinja templates
├── .claude/                # Claude Code: commands/, hooks/, settings, generated skills
├── .codex/ .opencode/      # Codex and OpenCode: generated skills + agents
├── .agents/                # Antigravity: generated skills + rules/GEMINI.md
├── .mcp.json               # Optional MCP servers (library docs, git) — opt-in
├── .mcp.example.json       # Example optional MCP expansions without secrets
├── Makefile               # Development commands
├── pyproject.toml         # Project configuration & dependencies
├── uv.lock                # Exact versions lockfile (DO NOT EDIT MANUALLY)
├── .pre-commit-config.yaml # Git hooks configuration
├── .editorconfig          # Editor formatting rules
└── README.md              # This file
```

## 🧭 AI Rules Structure (Cross-Tool)

This template uses a consistent four-level strategy so it can be reused with Claude Code, VS Code/Copilot, Antigravity rules, and Codex-style instructions.

### Level 1 — Governance

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

### Level 2 — Operational Skills

Internal governed skills live in `.github/skills/` (source of truth); vendored ones
in `.github/skills-external/`. The catalog is layered so a developer only needs the
**nine entrypoints**, by intent:

| I want to… | Use |
|---|---|
| start a project from this template | `bootstrap_project` |
| explore a scoped idea or compare options | `brainstorm_quick` |
| design a new subsystem or a design-impacting change | `brainstorming` |
| implement a feature or an approved plan | `plan_and_execute_feature` |
| fix a failing test, traceback or wrong behavior | `systematic_debugging` |
| plan a code, data or architecture migration | `generate_migration_plan` |
| check current facts (versions, APIs, releases) | `research_current_info` |
| verify the work before calling it done | `verify_changes` |
| review the finished diff | `requesting-code-review` |

The entrypoints compose the internal primitives (`create_domain_contract`,
`test-driven-development`, `generate_e2e_tests`, `retrospective`, …) and optional
specialists (`create_mle_agent_package`, `ui-ux-pro-max`). The full, generated
inventory with families, visibility and profiles is
[docs/generated/skills-catalog.md](docs/generated/skills-catalog.md); the guide is
[docs/skills-guide.md](docs/skills-guide.md).

Four tools read a **generated** native layout of the same governed skills —
`.claude/skills/`, `.codex/skills/`, `.opencode/skills/` (symlinks) and
`.agents/skills/` (copies + manifest). Copilot reads the governed paths directly.
One command refreshes everything, including the agents, the managed block inside
every adapter file, and the generated catalog:

```bash
make sync-skills     # then `make check-sync` verifies nothing is stale (CI gate)
```

Per-tool targets exist for narrower refreshes (`make setup-claude-skills`,
`make setup-opencode-skills`, `make setup-antigravity-skills`,
`make render-adapters`, `make sync-agents`, `make render-catalog`).

Agents may **recommend** git actions and prepare commands, diffs and PR text, but
never run `git commit`, `git push`, `merge`, `rebase` or a branch deletion on
their own. That `git-actions` policy is declared once in
`adapters/registry.toml`, rendered into every adapter, projected into each
vendored skill that instructs otherwise, and enforced as a real permission where
the platform has one (Claude Code, OpenCode; opt-in for Copilot). Matrix:
[docs/skills-guide.md](docs/skills-guide.md).

Engine reference: [docs/skills-management.md](docs/skills-management.md).

### Level 3 — Automation

- `.github/automation.md`
- CI and local checks through `make lint`, `make test`, and `make ci`
- On PRs, if `src/` or `tests/` changes, at least one file in `docs/` must be updated
- Test flow enforces `make format` and `make fix` before running tests

### Level 4 — Orchestration

- `.github/orchestration.md`
- Plan-first requirement
- Step-by-step execution
- Mandatory diff review
- Validation against automation
- No direct large generation without skill invocation

Adapters:

| Tool | Entrypoint (instructions) | Native skills | Native agents |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/skills/` | `.claude/agents/` |
| Codex | `AGENTS.md` | `.codex/skills/` | `.codex/agents/` |
| OpenCode | `OPENCODE.md` | `.opencode/skills/` | `.opencode/agents/` |
| Antigravity | `.agents/rules/GEMINI.md` | `.agents/skills/` | — |
| GitHub Copilot | `.github/copilot-instructions.md` | reads `.github/skills*` directly | — |

All generated from `.github/skills/`, `.github/skills-external/` and
`.github/agents/` by `make sync-skills`. Claude Code also ships slash commands in
`.claude/commands/`, including `/toolbelt` for MCP/CLI/service discovery.

Documentation template:

- `docs/implementation-template.md` (use it when implementing and testing new changes)

Self-hosted / local-model mode (`local_model_32k`):

- To develop with small self-hosted models (Qwen 3.x / 3.6, 27B-35B @ 32k), the recommended
  path is **OpenCode routed through your ai-gateway** (`make opencode`): plan with a strong
  cloud model, build local at $0, all visible in Langfuse. Start with the **"Priority order"**
  in [docs/local-model-runtime-config.md](docs/local-model-runtime-config.md) — the mechanical
  layer (gateway output cap, repetition penalty, served context) that makes a 32k model
  usable. Short operating rules: `LOCAL_AGENT.md`. Sizing heuristics:
  [docs/task-sizing.md](docs/task-sizing.md).
- To run that model on **your own Mac** (16 GB / 24 GB), follow
  [docs/local-model-mac-setup.md](docs/local-model-mac-setup.md) — the install path
  (LM Studio → local LiteLLM → OpenCode), the environment-variable contract, an honest
  memory budget, and which knob lives where. Gateway template:
  `gateway/config.example.yaml`.

## 🔁 Agentic Working Loop

Beyond the cross-tool rules above, this template ships an opinionated **working loop**
for AI-assisted development — optimized for Claude Code — so the high-quality path is
the path of least resistance:

**Ground → Plan → Delegate → Verify → Compound.**

| Piece | Where | Purpose |
|-------|-------|---------|
| Operating playbook | `CLAUDE.md` → *Operating playbook* | The loop as standing instructions for the agent. |
| Slash commands | `.claude/commands/` | `/plan`, `/orchestrate`, `/verify`, `/adr`, `/retro`. |
| Loop skills | `.github/skills/` | `systematic_debugging`, `verify_changes`, `retrospective` (+ existing planning/review skills). |
| Hooks (nudge) | `.claude/settings.json`, `.claude/hooks/` | Inject the loop at session start; remind to verify/compound when code changed. Non-blocking. |
| Memory | `memory/` | Persistent working memory (`context`, `learnings`, `patterns`) across sessions. |
| Decisions | `docs/adr/` | Architecture Decision Records — the durable "why". |
| MCP servers | `.mcp.json` | Optional extra tools (library docs via context7, git). Opt-in; require the tool to be installed. |
| Toolbelt guide | `docs/claude-toolbelt.md` | When to use MCP, CLI, Make targets, or local services before asking the user. |

Full guide: [docs/agentic-workflow.md](docs/agentic-workflow.md). How this maps to
assessments of AI-assisted coding skill (and what a template can/can't influence):
[docs/agentic-scoring.md](docs/agentic-scoring.md).

## 🔧 Available Commands

| Command | Description |
|---------|-------------|
| `make install` | Setup environment, install python version and sync dependencies |
| `make add PKG=x` | Add a new dependency to the project |
| `make remove PKG=x` | Remove a dependency from the project |
| `make setup-hooks` | Install pre-commit hooks for git |
| `make format` | Format code with Ruff |
| `make lint` | Run code quality checks |
| `make fix` | Auto-fix linting issues |
| `make test` | Run tests with coverage |
| `make check` | Read-only quality gate: format check, ruff, bandit, mypy, tests |
| `make check-sync` | Fail if any generated skill/agent/catalog artifact is stale |
| `make check-docs-coverage` | Fail if `src/`/`tests/` changed without a `docs/` update |
| `make typecheck` | Static type checking only (mypy) |
| `make ci` | Full read-only pipeline: `check` + `check-sync` + `check-docs-coverage` |
| `make toolbelt-doctor` | Check expected CLIs and configured local service endpoints |
| `make setup-claude-skills` | Generate `.claude/skills` native symlinks from governed skills |
| `make setup-antigravity-skills` | Generate `.agents/skills` native Antigravity mirror from governed skills |
| `make setup-opencode-skills` | Generate `.opencode/skills` native symlinks from governed skills |
| `make sync-agents` | Project `.github/agents/` into each tool's native agent format |
| `make render-adapters` | Regenerate the managed skills block inside every adapter file |
| `make sync-skills` | One-shot: ingest external skills, refresh `skills-lock.json`, all four native skill layouts, the agents, every adapter block, and the generated catalog |
| `make render-catalog` | Regenerate `docs/generated/skills-catalog.md` from the governed skills + registry |
| `make route PROMPT=…` | Route one request through the skills catalog (deterministic) |
| `make routing-eval` | Deterministic skill-routing scenarios (`tests/routing/`) |
| `make routing-eval-live` | Opt-in: same scenarios against a real model |
| `make purge-external-skills` | Remove all external skills and reset every native layout to internal-only |
| `make template-remote-setup` | Add or update the template upstream remote |
| `make template-sync` | Selective governance sync from a semver tag (recommended) |
| `make template-sync PREVIEW=1` | Preview the governance diff without applying |
| `make version` | Show the current version, the latest tag, and whether a release is pending |
| `make harness-change-summary` | Classify changes since the latest tag and print the next version number |
| `make new-version [VERSION=x]` | Step 1: bump `pyproject.toml` + scaffold CHANGELOG + refresh `uv.lock` |
| `make release-pr` | Step 2 (guarded): branch + commit the bump + push + open the release PR |
| `make publish-release` | Step 3 (guarded, on `main`): preflight → confirm → tag + Release + manifest |
| `make harness-release-check` | Read-only release preflight (never tags) |
| `make harness-release` | Manual fallback: preflight + **print** the publish commands |
| `make template-release VERSION=x` | Deprecated — refuses to run; use `make publish-release` |
| `make template-sync-preview` | Fetch template changes and preview incoming commits |
| `make template-sync-merge` | Merge full template branch into current branch |
| `make template-sync-rebase` | Rebase current branch onto full template branch |
| `make generate-requirements` | Export `uv.lock` to `requirements.txt` |
| `make clean` | Remove cache and generated files |
| `make help` | Show all available commands |

## Template Sync & Release

This template uses **semver tags** (`vX.Y.Z`) + a CHANGELOG so downstream projects can pin
to a specific version and adopt improvements incrementally.

**Check the current version at a glance** — `make version` prints the `pyproject.toml`
version (source of truth), the latest published tag, and whether a release is pending:

```bash
make version
# 📦 pyproject version : 0.2.0
# 🏷️  latest tag        : v0.2.0
# ✅ v0.2.0 is published.
```

### Cut a release (maintainers)

Releases are **guarded and traceable**: the tooling is read-only by default, and the
only two commands that mutate git (`make release-pr`, `make publish-release`) run
their full guard set first and then stop for an explicit `[y/N]` confirmation
(`make template-release` is deprecated and points here). You never invent the version
number — the tooling derives it — and you never type it twice: every target defaults
`VERSION` from `pyproject.toml` and `BASE_REF` from the latest tag.

> ⚠️ **The tag is the LAST step, never the first.**
> The version lives in `pyproject.toml` and `CHANGELOG.md`; the tag only *records* a
> commit that already carries it. `publish-release` creates the tag only after the
> whole preflight is green — because a published tag is never moved.

#### Step 0 — Land your work on `main` first

**The release flow starts from `main`, with everything you want to release already
merged.** It is not something you run from a feature branch, and the version is never
bumped on one.

| Where you are | What to do |
|---|---|
| On a feature branch, changes not merged yet | Commit, push, open a PR, merge it to `main`. Then come back here. |
| On `main`, everything merged | `git switch main && git pull --ff-only`, then Step 1. |

Two reasons this order is not optional:

- **The version number is derived from committed history.** `make new-version`
  classifies `git diff <latest tag>..HEAD` — commits, never your working tree. Run it
  with the work uncommitted and it sees nothing: it proposes a PATCH bump and
  scaffolds a `- TODO:` section instead of real notes.
- **The release commit carries only the bump.** `make release-pr` refuses
  (`unexpected_dirty`) when anything other than `pyproject.toml`, `CHANGELOG.md` and
  `uv.lock` is dirty, precisely so feature work cannot be swept into a release commit.

While you develop, `make version` keeps showing the last released number. That is
correct, not a problem to fix.

The whole flow is then three commands, all run on `main`:

#### Step 1 — Scaffold the bump

```bash
make new-version
# ✅ Prepared release 0.2.1: pyproject.toml + '## [0.2.1]' CHANGELOG section
```

It derives the number from the classified changes since the latest tag (SemVer —
**PATCH** = fix / docs / tooling · **MINOR** = new skill, agent, rule, or supported
tool · **MAJOR** = removal, rename, or breaking change), writes it into
`pyproject.toml`, scaffolds the CHANGELOG section from the commit subjects, and
refreshes `uv.lock`. It refuses to run if the version doesn't increase, the tag
already exists, the CHANGELOG section is already there — or a previous release is
reconciled but not yet tagged (publish that one first).

Because the number comes from that classified diff, a release that **removes** a file
or touches a **platform** path (the sync engine, `Makefile`, `adapters/registry.toml`)
is classified MAJOR, not MINOR. Disagree with the derived number? Pass it explicitly:
`make new-version VERSION=X.Y.Z`.

Then **edit the CHANGELOG bullets by hand**: they start as raw commit subjects — turn
them into human release notes. If you kept notes under a `## [Unreleased]` heading
while working, move them into the new `## [X.Y.Z]` section now: the scaffold is
inserted above the first existing section and is built from commit subjects, so notes
written anywhere else are not picked up.

#### Step 2 — Open the release PR

```bash
make release-pr        # add DRY_RUN=1 to preview, YES=1 to skip the prompt
```

After its guards pass (curated CHANGELOG, only the bump files dirty, no tag, `gh`
available) and you confirm, it creates `release/vX.Y.Z`, commits exactly
`pyproject.toml` + `CHANGELOG.md` + `uv.lock`, pushes, and opens the PR. Review and
merge it to `main`.

#### Step 3 — Publish (after the merge)

```bash
git switch main && git pull --ff-only
make publish-release   # preflight (runs the gates) → [y/N] → tag + Release + manifest
```

It refuses to run off `main`, out of sync with `origin/main`, or with a red
preflight. After you confirm, it runs the whole publish sequence: annotated tag →
push → GitHub Release (notes taken from your curated CHANGELOG section) → release
manifest (timestamp stamped automatically) → asset upload. If a step fails
mid-sequence, nothing is rolled back (a pushed tag is immutable) and it prints the
exact remaining commands to finish by hand.

Prefer to type the commands yourself? `make harness-release` runs the same preflight
and **prints** the sequence without executing it. Full policy and provenance flags:
[docs/harness-release-lifecycle.md](docs/harness-release-lifecycle.md).

#### If the preflight fails

Each code names a precondition. Fix the precondition — never bypass the check
(`SKIP_GATES=1` skips `make check` only; these problems stay).

| Code | What it means | Fix |
|---|---|---|
| `version_mismatch` | `pyproject.toml` still holds the old version | Do Step 1: `make new-version` |
| `changelog_missing` | No `## [X.Y.Z]` section in `CHANGELOG.md` | Do Step 1: `make new-version` |
| `changelog_todo` | The CHANGELOG section still has the scaffold `- TODO:` bullet | Curate the release notes, then re-run `make release-pr` |
| `tag_exists` | The tag was created before Steps 1–2 | See below — never move a published tag |
| `dirty_tree` | Uncommitted changes at publish time | Commit or stash, then re-run |
| `nothing_to_commit` | `make release-pr` found a clean tree | Run `make new-version` first (or the bump is already committed — open the PR by hand) |
| `unexpected_dirty` | Files beyond `pyproject.toml`/`CHANGELOG.md`/`uv.lock` are dirty | Commit or stash them — the release commit carries only the bump |
| `branch_exists` | `release/vX.Y.Z` exists and is not checked out | Switch to it or delete it |
| `off_main` / `out_of_sync` | `make publish-release` run off `main`, or main ≠ `origin/main` | `git switch main && git pull --ff-only` |
| `gh_missing` | GitHub CLI not on PATH | `brew install gh && gh auth login` |
| `platform_change` | The release touches platform paths beyond the bump pair | Split into a separate reviewed PR with a migration note |
| `invalid_semver` | `VERSION` is not `MAJOR.MINOR.PATCH` | Take the derived number (don't pass `VERSION` at all) |

**About `platform_change`** — `pyproject.toml` and `uv.lock` are platform paths, and
the Step 1 bump necessarily touches both. The preflight recognizes that exact pair and
auto-allows it (you'll see an "auto-allowed" note). If *anything else* appears in the
platform list (the sync engine, `Makefile`, `registry.toml`), it is a real platform
change: split it into its own reviewed PR with a migration note. `ALLOW_PLATFORM=1`
exists for that reviewed case only.

**Recovering from `tag_exists`** — you tagged too early, so the tag points at a commit
that does not carry the version. Never fix this by editing the files to match the tag;
that inverts the source of truth. Check whether it was actually published:

```bash
gh release list          # is there a Release for vX.Y.Z?
```

- **No Release and no downstream consumer** — the tag is noise. Delete it, then
  resume the flow (`make release-pr` if the bump isn't merged yet, otherwise
  `make publish-release` on `main`):

  ```bash
  git tag -d vX.Y.Z
  git push origin :refs/tags/vX.Y.Z
  ```

- **Already published or adopted downstream** — leave it alone. Reconcile the two files
  to the *next* version and release that one instead.

### For downstream projects — adopt a release

```bash
# Selective sync: governance layer only (skills, agents, rules, adapter templates)
# Does NOT touch src/, Makefile, data/, or the skills_sync engine
make template-sync REF=v0.3.0        # adopt a specific version
make template-sync                    # adopt the latest v* tag
make template-sync PREVIEW=1          # inspect the diff before applying
make template-sync TOOL=opencode      # regenerate only one tool's adapter
```

Review with `git diff`, then `make check-sync && make check`, then commit on a branch.

> **Sync protocol.** `adapters/registry.toml` declares a `[template_sync].protocol`
> (currently **2**). Governance files are safe to adopt on their own only while the
> release's protocol matches yours: protocol 2 ships adapter templates that need the
> v2 `skills_sync` engine and the registry's `[catalog]` blocks, both of which are
> *platform* paths. Adopting a release with a higher protocol therefore means taking
> the platform upgrade first, in its own reviewed PR — the preview refuses otherwise.
> Migration steps for a repository that vendors the engine:
> [docs/skills-catalog-v3-audit.md](docs/skills-catalog-v3-audit.md).

For the **full release cycle** (when to tag, semver rules, bootstrap for older projects),
see [docs/updating-existing-projects.md](docs/updating-existing-projects.md).
For the full sync workflow (conflict resolution, full-repo merge/rebase option),
see [docs/template-sync.md](docs/template-sync.md).

## 🧩 Skills Lifecycle (Template)

### Default skills bundled in this template

The bundled catalog (internal and vendored) is generated on every sync into
[docs/generated/skills-catalog.md](docs/generated/skills-catalog.md) — do not
maintain a copy of it here. Retired names (`execute_engineering_task`,
`create_use_case`, `create_repository_interface`, `source-command-*`) resolve to
their replacements through `[alias.*]` in `adapters/registry.toml`.

### Install an external skill from skills.sh

Use the skills installer CLI (example):

```bash
npx skills add https://github.com/mindrally/skills --skill odoo-development
```

Then normalize it into this repository structure:

```bash
make sync-skills
```

This syncs complete skill directories to `.github/skills-external/`, refreshes
`skills-lock.json` (hash, upstream and licence per skill), removes installer temp
folders, and then rebuilds **every** projection: the four native skill layouts, the
governed agents, the managed block in each adapter file, and
`docs/generated/skills-catalog.md`. There is no separate step for internal skills —
`make sync-skills` covers both sources; `make check-sync` then fails if anything is
stale.

The Antigravity mirror is copied rather than symlinked and writes a hidden manifest,
so generated skills are not re-imported as ad-hoc ones on the next run.

A vendored skill also needs an `[external_skill.<name>]` entry (upstream + licence,
or `make check` fails), a `[skill.<name>]` overlay for its catalog metadata, and —
if its body instructs commits, pushes or merges — an entry in
`[policy.git-actions].applies_to`. Details in
[CONTRIBUTING.md](CONTRIBUTING.md) and [docs/skills-guide.md](docs/skills-guide.md).

### Purge all external skills (reset mode)

To test the full lifecycle from scratch:

```bash
make purge-external-skills
```

This removes all synced external skills and `skills-lock.json`, while keeping internal template skills untouched.

## 📝 Configuration

- **Dependencies**: `pyproject.toml` - `[project.dependencies]`
- **Ruff**: `pyproject.toml` - `[tool.ruff]`
- **Pytest**: `pyproject.toml` - `[tool.pytest.ini_options]`
- **Editor**: `.editorconfig`

## 🔩 Harness Engineering Reference

This template is the **reference implementation** of a harness engineering approach:
governance rules, operational skills, automation gates, and orchestration policies are
encoded directly in the repo so every AI assistant reads them on first load — no manual
prompting required.

The full methodology lives in a separate public guide (`harness-engineering-guide`).
This repo ships the operational layer that derived projects inherit; the documents
below are the entry points.

Key documents:

- [docs/claude-toolbelt.md](docs/claude-toolbelt.md) — operational MCP, CLI, Make,
  and local-service toolbelt for Claude Code.
- [docs/harness-engineering.md](docs/harness-engineering.md) — what harness engineering
  means here, how the four-level rule system works, and what must never be added to this
  template.
- [docs/harness-architecture.md](docs/harness-architecture.md) — the projection engine
  that pushes rules into Claude Code, Copilot, Antigravity, OpenCode, and Codex.
- [docs/open-source-readiness.md](docs/open-source-readiness.md) — checklist before
  making this repo or any derived repo publicly available.

## 🤝 Contributing

1. Create a new branch
2. Make your changes
3. Run `make ci` to ensure quality
4. Submit a pull request

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).

This repository vendors third-party agent skills under `.github/skills-external/`.
They keep their own licences; attribution is in [NOTICE](NOTICE) and machine-readable
provenance in `skills-lock.json`.
