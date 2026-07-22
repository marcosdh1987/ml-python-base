# Python ML Base Project

A modern Python base project template with best practices for machine learning and data science development.

## 🚀 Features

- **Modern Python 3.11** setup with `uv` for ultra-fast dependency management
- **Reproducible Environments** using `uv.lock`
- **Ruff** for ultra-fast linting and formatting (replaces Black, Flake8, isort, pyupgrade)
- **Jupyter Notebooks** support with automated cleanup (`nbstripout`)
- **Pre-commit hooks** to ensure quality before committing
- **Makefile** commands for common development tasks
- **Testing** setup with pytest and coverage
- **Docker** support for containerization
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
```� Dev Containers (Recommended)

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

## �

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

The project provides three main levels of code quality checks:

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

# 4. Run full CI pipeline (Fix + Lint + Test)
make ci
```

## 📁 Project Structure

```
.
├── src/                    # Source code
├── tests/                  # Test files
├── notebooks/              # Jupyter notebooks
├── memory/                 # Persistent project memory (context, learnings, patterns)
├── docs/                   # Documentation, including:
│   └── adr/                #   Architecture Decision Records (the durable "why")
├── .claude/                # Claude Code harness: commands/, hooks/, settings, skills
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

Internal governed skills are stored in `.github/skills/` as the source of truth:

- `create_use_case`
- `create_repository_interface`
- `create_mle_agent_package`
- `generate_e2e_tests`
- `generate_implementation_docs`
- `refactor_to_clean_architecture`
- `validate_module_structure`
- `generate_migration_plan`
- `execute_engineering_task`
- `plan_and_execute_feature`

Claude Code reads a generated native layout from `.claude/skills/`, including internal and synced external skills. Refresh it with:

```bash
make setup-claude-skills
```

Antigravity reads a generated native workspace layout from `.agents/skills/` and `.agents/rules/`. Refresh the skills mirror with:

```bash
make setup-antigravity-skills
```

External synced/vendor skills live in `.github/skills-external/`.

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

- Claude Code entrypoint: `CLAUDE.md`
- Claude Code native skills: `.claude/skills/` generated from `.github/skills/` and `.github/skills-external/`
- Claude Code slash commands: `.claude/commands/`, including `/toolbelt` for MCP/CLI/service discovery
- Copilot entrypoint: `.github/copilot-instructions.md`
- Antigravity workspace rules: `.agents/rules/`
- Antigravity native skills: `.agents/skills/` generated from `.github/skills/` and `.github/skills-external/`

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
| `make ci` | Run full CI pipeline |
| `make toolbelt-doctor` | Check expected CLIs and configured local service endpoints |
| `make setup-claude-skills` | Generate `.claude/skills` native symlinks from governed skills |
| `make setup-antigravity-skills` | Generate `.agents/skills` native Antigravity mirror from governed skills |
| `make sync-skills` | Sync external skills, refresh `skills-lock.json`, and refresh Claude and Antigravity native skill layouts |
| `make purge-external-skills` | Remove all external skills and refresh Claude and Antigravity native skill layouts |
| `make template-remote-setup` | Add or update the template upstream remote |
| `make template-sync` | Selective governance sync from a semver tag (recommended) |
| `make template-sync PREVIEW=1` | Preview the governance diff without applying |
| `make template-release VERSION=x` | Tag a semver release of this template |
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

Releases are **manual and traceable**: the tooling validates and prints commands but
never commits, tags, pushes, or publishes (`make template-release` is deprecated and
points here). Everything below uses **one version number** — and you don't invent it,
the tooling tells you.

#### Step 1 — Get the next version number

```bash
make harness-change-summary BASE_REF=$(git describe --tags --abbrev=0)
# 👉 Recommended bump: PATCH  (current 0.2.0 → next 0.2.1)
#    Use this version in pyproject.toml, CHANGELOG.md, and the release: 0.2.1
```

That number follows SemVer — **PATCH** = fix / docs / tooling · **MINOR** = new skill,
agent, rule, or supported tool · **MAJOR** = removal, rename, or breaking change. Use
it as the `VERSION` everywhere below (this example uses `0.2.1`).

#### Step 2 — Put that number in two files, then PR + merge

| File | What to change |
|---|---|
| `pyproject.toml` | `version = "0.2.1"` |
| `CHANGELOG.md` | add a `## [0.2.1]` section at the top, listing the changes |

Commit on a branch, open a PR, and merge to `main`.

#### Step 3 — Publish (after the merge)

Replace `0.2.1` with your number and copy-paste the whole block:

```bash
git switch main && git pull --ff-only
make harness-release VERSION=0.2.1        # preflight (runs the gates) + prints these
git tag -a v0.2.1 -m "Template release v0.2.1"
git push origin v0.2.1
gh release create v0.2.1 --title v0.2.1 --notes "Template release v0.2.1"
make harness-release-manifest VERSION=0.2.1 PUBLISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
gh release upload v0.2.1 dist/harness-release-v0.2.1.yaml
```

`make harness-release` refuses to proceed unless `pyproject.toml` and `CHANGELOG.md`
match the version, the tag is new, and the tree is clean — so if Step 2 was skipped it
stops you with a clear message. Full policy and provenance flags:
[docs/harness-release-lifecycle.md](docs/harness-release-lifecycle.md).

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

For the **full release cycle** (when to tag, semver rules, bootstrap for older projects),
see [docs/updating-existing-projects.md](docs/updating-existing-projects.md).
For the full sync workflow (conflict resolution, full-repo merge/rebase option),
see [docs/template-sync.md](docs/template-sync.md).

## 🧩 Skills Lifecycle (Template)

### Default skills bundled in this template

Internal curated skills live in `.github/skills/`:

- `create_use_case`
- `create_repository_interface`
- `create_mle_agent_package`
- `generate_e2e_tests`
- `generate_implementation_docs`
- `refactor_to_clean_architecture`
- `validate_module_structure`
- `generate_migration_plan`
- `execute_engineering_task`
- `plan_and_execute_feature`

### Install an external skill from skills.sh

Use the skills installer CLI (example):

```bash
npx skills add https://github.com/mindrally/skills --skill odoo-development
```

Then normalize it into this repository structure:

```bash
make sync-skills
```

This syncs complete skill directories to `.github/skills-external/`, refreshes `skills-lock.json`, removes installer temp folders, and refreshes `.claude/skills`. Run `make setup-claude-skills` separately when internal governed skills change and Claude Code needs its native links refreshed.

After sync, the repo also regenerates `.agents/skills/` so Antigravity can discover the governed internal and synced external skills natively. The generated Antigravity mirror writes a hidden manifest to avoid re-importing generated skills on the next `make sync-skills` run.

### Purge all external skills (reset mode)

To test the full lifecycle from scratch:

```bash
make purge-external-skills
```

This removes all synced external skills and `skills-lock.json`, while keeping internal template skills untouched.

## 🐳 Docker Support

```bash
# Build Docker image
make build-api

# Run in Docker
make run-api-docker

# Stop Docker container
make stop-docker
```

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
This repo ships only the operational layer that derived projects inherit.

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

This is a template project - customize as needed for your use case.
