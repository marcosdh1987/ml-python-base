---
trigger: always_on
---

# Antigravity Workspace Rule

Use this repository's governed structure as the canonical source of truth.

## Governance

Read and apply:

- @.github/architecture.md
- @.github/standards.md
- @.github/domain-boundaries.md

## Skills

Antigravity discovers workspace-native skills from:

- @.agents/skills/

The governed sources remain:

- @.github/skills/
- @.github/skills-external/

Refresh the Antigravity-native layout with:

- `make setup-antigravity-skills`
- `make sync-skills`

If an internal governed skill and an external synced skill share the same name, prefer the internal governed skill.

<!-- BEGIN GENERATED SKILLS (managed by skills_sync; do not edit) -->
The governed skills below are projected into `@.agents/skills/`. Internal skills are the source of truth and take precedence over external synced skills on name conflicts.

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

## Automation And Orchestration

Read and follow:

- @.github/automation.md
- @.github/orchestration.md

## Agents And SDLC

- @.github/agents/ — governed, tool-agnostic agent definitions.
- @.github/sdlc.md — lifecycle phases gated by `make` targets.
- @.github/portability.md — model tier abstraction and self-hosted fallback design.

## Runtime Rules

- Interact in the same language as the user.
- Keep all code artifacts in English.
- Prefer `make` targets and `uv` workflows.
- Update docs in `docs/` when implementation or tests change.
- Use absolute imports only.
