# OpenCode Adapter

Use this repository-level structure as the canonical source of instructions.

## Level 1 — Governance

Always read and apply these files before generating code or plans:

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

## Level 2 — Operational Skills

Each skill exposes a `SKILL.md` file with purpose, required input, output format, and execution rules.
When a task matches a skill, read its `SKILL.md` before generating code or plans.

<!-- BEGIN GENERATED SKILLS (managed by skills_sync; do not edit) -->
The governed skills below are projected into `.opencode/skills/`. Internal skills are the source of truth and take precedence over external synced skills on name conflicts.

**Internal skills:**

- `create_mle_agent_package` — Use when designing a reusable pip-installable MLE agent package with governed scaffolding, runtime adapters, and validation plans.
- `create_repository_interface` — Use when defining repository interfaces that isolate persistence details from domain and application logic.
- `create_use_case` — Use when creating an application use case with clean architecture boundaries, typed contracts, and explicit business flow.
- `execute_engineering_task` — Use when implementing a feature, fixing a bug, or executing scoped engineering work through governed orchestration.
- `generate_e2e_tests` — Use when generating end-to-end tests for critical user, API, CLI, or service flows.
- `generate_implementation_docs` — Use when creating or updating implementation documentation for completed code or test changes.
- `generate_migration_plan` — Use when planning low-risk code, data, or architecture migrations with validation and rollback steps.
- `plan_and_execute_feature` — Use when delivering a feature through explicit planning, phased execution, validation, and governed handoff.
- `refactor_to_clean_architecture` — Use when refactoring modules to align dependency direction, responsibilities, and boundaries with clean architecture.
- `validate_module_structure` — Use when validating module placement, dependency direction, and structure against repository governance.

**External synced skills:**

- `ui-ux-pro-max` — UI/UX design intelligence for web and mobile. Includes 50+ styles, 161 color palettes, 57 font pairings, 161 product types, 99 UX guidelines, and 25 chart types across 10 stacks (React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui, and HTML/CSS). Actions: plan, build, create, design, implement, review, fix, improve, optimize, enhance, refactor, and check UI/UX code. Projects: website, landing page, dashboard, admin panel, e-commerce, SaaS, portfolio, blog, and mobile app. Elements: button, modal, navbar, sidebar, card, table, form, and chart. Styles: glassmorphism, claymorphism, minimalism, brutalism, neumorphism, bento grid, dark mode, responsive, skeuomorphism, and flat design. Topics: color systems, accessibility, animation, layout, typography, font pairing, spacing, interaction states, shadow, and gradient. Integrations: shadcn/ui MCP for component search and examples.

Refresh this layout with `make sync-skills` (or `make check-sync` to verify it is current).
<!-- END GENERATED SKILLS -->

## Level 3 — Automation

Prefer system-enforced quality over model-only behavior:

- Automation policy: `.github/automation.md`
- Quality gate sequence: `make format` → `make fix` → `make lint` → `make test`

Check `Makefile` before suggesting commands.

## Level 4 — Orchestration

Use explicit orchestration for complex tasks:

- Orchestration policy: `.github/orchestration.md`
- Plan first, then execute.
- Complete each phase before moving to the next.
- Review diffs before finalizing.
- Validate results against automation requirements.
- Do not generate large outputs without first invoking the relevant skill.

## Level 5 — Agents and SDLC

- Governed, tool-agnostic agents live in `.github/agents/`; OpenCode native agents
  are generated into `.opencode/agent/` (refresh with `make sync-agents`).
- The lifecycle (plan -> implement -> test -> document -> review) and its `make`
  exit gates are defined in `.github/sdlc.md`.
- Runtime/model portability for self-hosted fallback (Ollama / LM Studio) and the
  `planner`/`executor`/`fast` tier abstraction: `.github/portability.md`.

## Runtime Rules

- Interact in the same language as the user.
- Keep all code artifacts in English (identifiers, docstrings, comments, docs).
- Prefer `make` targets and `uv` workflows.
- When implementing or testing changes, create or update documentation in `docs/`.
- Use absolute imports only.
