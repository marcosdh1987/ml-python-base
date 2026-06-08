# Claude Code Adapter

Use this repository-level structure as the canonical source of instructions.

## Governance

Always read and apply these files before generating code or plans:

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

## Native Skills

Claude Code discovers internal and synced external skills from:

- `.claude/skills/`

Generate or refresh that native layout with:

- `make setup-claude-skills`

The governed internal source of truth remains:

- `.github/skills/`

External synced/vendor skills remain in:

- `.github/skills-external/`

Antigravity uses a separate generated native workspace mirror at:

- `.agents/skills/`

If overlap exists, prefer `.github/skills/` over `.github/skills-external/`.

<!-- BEGIN GENERATED SKILLS (managed by skills_sync; do not edit) -->
The governed skills below are projected into `.claude/skills/`. Internal skills are the source of truth and take precedence over external synced skills on name conflicts.

**Internal skills:**

- `create_domain_contract` — Use when defining a typed domain contract — an application use case (business flow) or a repository interface (persistence boundary) — with clean architecture boundaries.
- `create_mle_agent_package` — Use when designing a reusable pip-installable MLE agent package with governed scaffolding, runtime adapters, and validation plans.
- `generate_e2e_tests` — Use when generating end-to-end tests for critical user, API, CLI, or service flows.
- `generate_implementation_docs` — Use when creating or updating implementation documentation for completed code or test changes.
- `generate_migration_plan` — Use when planning low-risk code, data, or architecture migrations with validation and rollback steps.
- `plan_and_execute_feature` — Use when delivering a feature through explicit planning, phased execution, validation, and governed handoff — or when implementing/fixing already-scoped engineering work via the execute_only mode.
- `refactor_to_clean_architecture` — Use when refactoring modules to align dependency direction, responsibilities, and boundaries with clean architecture.
- `validate_module_structure` — Use when validating module placement, dependency direction, and structure against repository governance.

**External synced skills:**

- `ui-ux-pro-max` — UI/UX design intelligence for web and mobile. Includes 50+ styles, 161 color palettes, 57 font pairings, 161 product types, 99 UX guidelines, and 25 chart types across 10 stacks (React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui, and HTML/CSS). Actions: plan, build, create, design, implement, review, fix, improve, optimize, enhance, refactor, and check UI/UX code. Projects: website, landing page, dashboard, admin panel, e-commerce, SaaS, portfolio, blog, and mobile app. Elements: button, modal, navbar, sidebar, card, table, form, and chart. Styles: glassmorphism, claymorphism, minimalism, brutalism, neumorphism, bento grid, dark mode, responsive, skeuomorphism, and flat design. Topics: color systems, accessibility, animation, layout, typography, font pairing, spacing, interaction states, shadow, and gradient. Integrations: shadcn/ui MCP for component search and examples.

Refresh this layout with `make sync-skills` (or `make check-sync` to verify it is current).
<!-- END GENERATED SKILLS -->

## Automation

Prefer system-enforced quality over model-only behavior:

- Automation policy: `.github/automation.md`
- Local sequence: `make format` -> `make fix`; CI-safe gate: `make check`.
- CI is read-only (`make ci` = `make check` + `make check-sync`) — never relies on
  CI to format or fix.

Check `Makefile` before suggesting commands.

## Orchestration

Use explicit orchestration for complex tasks:

- Orchestration policy: `.github/orchestration.md`
- Plan first, then execute.
- Complete each phase before moving to the next.
- Review diffs before finalizing.
- Validate results against automation requirements.

## Agents and SDLC

- Governed, tool-agnostic agents live in `.github/agents/`; their Claude Code
  native subagents are generated into `.claude/agents/` (refresh with
  `make sync-agents`).
- The AI-assisted lifecycle (plan -> implement -> test -> document -> review) with
  its `make` exit gates is defined in `.github/sdlc.md`.
- Runtime/model portability and the `planner`/`executor`/`fast` tier abstraction
  are documented in `.github/portability.md`.

## Runtime Rules

- Interact in the same language as the user.
- Keep all code artifacts in English (identifiers, docstrings, comments, docs).
- Prefer `make` targets and `uv` workflows.
- When implementing or testing changes, create or update documentation in `docs/`.
- Use absolute imports only.
