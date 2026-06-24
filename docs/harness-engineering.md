# Harness Engineering Reference

This repository is the **reference implementation** of a harness engineering approach for
AI-assisted Python/ML projects. A separate, educationally-focused repository —
`harness-engineering-guide` — contains the full methodology, rationale, and extended
examples. This document explains how the approach is realized here so that any repo
created from this template starts with the harness already in place.

---

## What is harness engineering (in this context)?

Harness engineering is the practice of encoding team standards, workflow rules, and
domain boundaries directly into the repository in a form that every AI coding assistant
can read and act on — rather than relying on per-session prompting or tribal knowledge.

The result is a **self-describing repo**: an agent that opens it for the first time
receives the same governance as a senior team member who has read every convention doc.

---

## How the rule system is organized

The harness is structured in four levels, each with a well-defined responsibility:

### Level 1 — Governance (static, binding)

High-level architecture decisions, coding standards, and domain boundaries that all
agents must respect before generating any code or plan.

| File | Purpose |
|---|---|
| `.github/architecture.md` | System design decisions and architectural constraints |
| `.github/standards.md` | Coding conventions, naming rules, quality bar |
| `.github/domain-boundaries.md` | Bounded contexts and inter-module rules |

### Level 2 — Operational Skills (reusable, composable)

Governed, tool-agnostic workflow recipes that agents invoke for recurring tasks (create a
use case, generate tests, refactor to clean architecture, etc.).

| Location | Contents |
|---|---|
| `.github/skills/` | Internal curated skills (source of truth) |
| `.github/skills-external/` | Synced external/vendor skills |

Internal skills take precedence over external skills when both define the same name.

### Level 3 — Automation (system-enforced quality)

CI and local quality gates that replace model-only behavior with hard checks.

| File | Purpose |
|---|---|
| `.github/automation.md` | Policy for what automation enforces and when |

Local gate: `make format` → `make fix` → `make check`.
CI gate: `make ci` = `make check` + `make check-sync` (read-only, never fixes).

### Level 4 — Orchestration (complex task governance)

Rules that require agents to plan before acting, execute step by step, review diffs, and
validate against automation before finalizing.

| File | Purpose |
|---|---|
| `.github/orchestration.md` | Orchestration policy and agent collaboration rules |

---

## Source-of-truth files

The canonical governance layer lives exclusively in `.github/`:

```
.github/
  architecture.md          L1 — architecture decisions
  standards.md             L1 — coding standards
  domain-boundaries.md     L1 — module/context boundaries
  automation.md            L3 — automation policy
  orchestration.md         L4 — orchestration rules
  sdlc.md                  L5 — AI-assisted lifecycle (plan → implement → test → doc → review)
  portability.md           L5 — model tier abstraction and self-hosted fallback
  skills/                  L2 — internal governed skills
  skills-external/         L2 — synced external skills
  agents/                  L5 — tool-agnostic agent definitions
```

Generated outputs (never hand-edited): `.claude/skills/`, `.agents/skills/`,
`.opencode/skills/`, `.codex/skills/`, `skills-lock.json`, and the
`<!-- BEGIN/END GENERATED SKILLS -->` regions inside each adapter file.

---

## How rules are projected to AI tools

A single projection engine (`src/ml_python_base/skills_sync`) reads the governance layer
and writes tool-native layouts so each assistant finds rules exactly where it expects them:

| Tool | Entrypoint | Native skills dir | Refresh command |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/skills/` | `make setup-claude-skills` |
| VS Code / Copilot | `.github/copilot-instructions.md` | — (reads `.github/` directly) | `make sync-skills` |
| Antigravity | `AGENTS.md` | `.agents/skills/` | `make setup-antigravity-skills` |
| OpenCode | `OPENCODE.md` | `.opencode/skills/` | `make sync-skills` |
| Codex | `.codex/` adapter | `.codex/skills/` | `make sync-skills` |

To sync all tools at once after changing a skill or adding a new one:

```bash
make sync-skills
```

To add a new AI tool, add one `[[tool]]` entry to `adapters/registry.toml` and a Jinja2
template in `adapters/templates/`. No Makefile change needed. Full guide:
[docs/harness-architecture.md](harness-architecture.md).

---

## What must NOT be added to this repo

To keep the template lean, safe, and inheritable, the following are explicitly out of
scope:

- **No GitHub Pages** — no `mkdocs.yml`, no `docs/_config.yml`, no static-site config.
- **No publication workflows** — no `.github/workflows/pages.yml` or equivalent.
  Repos created from this template must not inherit a public-site pipeline.
- **No sensitive material** — no client names, credentials, private prompts, or
  commercially sensitive rules. All governance files must be safe for future open-source
  publication.
- **No long-form educational content** — extended methodology guides and tutorials belong
  in `harness-engineering-guide`, not here. This repo ships only the operational layer.
- **No non-English code artifacts** — identifiers, docstrings, comments, and all
  technical files must be in English (interaction with the user may be in any language).

---

## Related documents

- [docs/harness-architecture.md](harness-architecture.md) — projection engine internals
  and how to add a new AI tool.
- [docs/agentic-workflow.md](agentic-workflow.md) — the working loop (Ground → Plan →
  Delegate → Verify → Compound) that the harness enforces.
- [docs/open-source-readiness.md](open-source-readiness.md) — checklist before making
  this repo or a derived repo publicly available.
