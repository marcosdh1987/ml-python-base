# Codex UI Adapter

Use this repository-level structure as the canonical source of instructions.

## Level 1 — Governance

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

## Working loop

Default working loop for this repository: **Ground → Plan → Delegate → Verify →
Compound.** Read `memory/context.md` and `memory/learnings.md` before starting
when they exist in the workspace (in a foreign workspace these instructions
already carry the rules — proceed); explore before editing; verify with the
repo's own gate / tests (here: `make check`); record decisions in `docs/adr/`
and durable learnings in `memory/`. Full guide: `docs/agentic-workflow.md`.

## Debugging protocol

Mandatory ordered checklist for any bug fix or failing test. Canonical loop:
`.github/skills/systematic_debugging.md` (a workflow to follow — see Do not, below).

1. **Pin the working root first.** Run `pwd` and `ls`. The root is the directory
   that contains the failing code — look for `.git` or the failing test's path
   (in this template: `Makefile`, `pyproject.toml`, `src/`). State it once and
   prefix every later path with it. If a path errors, do not retry it: run one
   `find <root> -name <file>` and use the path it prints.
2. **Open the evidence.** From that root, read the failing test file and the
   implementation it exercises before planning any change.
3. **Restate the failure.** In 1–2 lines: the exact exception type and message,
   the operand values involved, and the failing call site (file:line). Propose no
   fix before this restatement.
4. **Reproduce with the repo's own runner.** Before editing, run the failing test
   once via the repo's documented gate or runner (check `Makefile`, `tox.ini`,
   `scripts/`; here: `make test` / `uv run pytest`). If none, use
   `python -m pytest <test> -x`; if pytest is missing, execute the real test
   file's functions directly. Never write a new script that approximates the test.
5. **One hypothesis at a time.** State a single root-cause hypothesis and probe it
   with one command. After two probes that fail to confirm, stop, re-read the
   evidence, and reframe — do not stack guesses or edits.
6. **Failed edit → smaller edit.** If an edit does not apply, re-read only the
   ~10 lines around the target, rebuild the old text from that exact output, and
   retry with a smaller hunk. After each edit batch, parse-check the changed
   files (`python -m py_compile <files>`) before any test run.
7. **Close only on a green rerun.** Re-run the exact step-4 command; done means it
   passes. If it still fails, make a new change or take the next diagnostic step —
   never re-read unchanged code, and never claim success without that rerun.

Do not:

- Do not invoke `systematic_debugging` as an agent or subagent. It is a skill
  (a workflow you read and follow); agents live in `.github/agents/`.
- Do not declare a diagnosis without the step-3 restatement.
- Do not substitute a parse check, a re-read, or a synthetic script for running
  the real test.

## Level 2 — Operational Skills

<!-- BEGIN GENERATED SKILLS (managed by skills_sync; do not edit) -->
The governed skills below are projected into `.codex/skills/`. Internal skills are the source of truth and take precedence over external synced skills on name conflicts.

**Internal skills:**

- `bootstrap_company_brain` — Use when instantiating this company-brain template for a new organization — guides the interview-and-mine process that fills domain, glossary, conventions, architecture and ownership from real sources (repos, docs, team interviews), replacing every _PENDIENTE_ marker with verified content.
- `bootstrap_project` — Use when starting a new project from a fresh clone of this template — guides the rename via `make init`, environment setup, template-remote configuration, and the first green quality gate, in any supported AI tool.
- `brainstorm_quick` — Use for fast ideation on a scoped feature when no written spec or formal approval is needed — diverge on options, weigh trade-offs, converge on a recommendation, then hand off to `plan_and_execute_feature`. For new features or design-impacting work that needs a written, user-approved spec, use the external `brainstorming` skill (full design gate) instead.
- `create_domain_contract` — Use when defining a typed domain contract — an application use case (business flow) or a repository interface (persistence boundary) — with clean architecture boundaries.
- `create_mle_agent_package` — Use when designing a reusable pip-installable MLE agent package with governed scaffolding, runtime adapters, and validation plans.
- `generate_e2e_tests` — Use when generating end-to-end tests for critical user, API, CLI, or service flows.
- `generate_implementation_docs` — Use when creating or updating implementation documentation for completed code or test changes.
- `generate_migration_plan` — Use when planning low-risk code, data, or architecture migrations with validation and rollback steps.
- `plan_and_execute_feature` — Use when delivering a feature through explicit planning, phased execution, validation, and governed handoff — or when implementing/fixing already-scoped engineering work via the execute_only mode.
- `refactor_to_clean_architecture` — Use when refactoring modules to align dependency direction, responsibilities, and boundaries with clean architecture.
- `research_current_info` — Use when the user asks for up-to-date or current information, to confirm something is still accurate, or when a task depends on facts that may have changed since training (library versions, APIs, pricing, releases, news, current best practices). Runs a governed web search with a curated domain allow/deny policy and cited, recency-checked results.
- `retrospective` — Use at the end of a unit of work to capture durable, non-obvious knowledge into project memory (memory/) and flag decisions worth an ADR. Turns one-off discoveries into compounding, persistent context.
- `systematic_debugging` — Use when diagnosing a bug, failing test, or unexpected behavior — drive a methodical reproduce → isolate → hypothesize → fix → verify loop instead of guessing. Prevents thrashing and repeated edits to the same file.
- `validate_module_structure` — Use when validating module placement, dependency direction, and structure against repository governance.
- `verify_changes` — Use before considering work done — run the read-only quality gate and tests, interpret failures, and confirm the change is correct. The verification step of the working loop.

**External synced skills:**

- `brainstorming` — You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation.
- `executing-plans` — Use when you have a written implementation plan to execute in a separate session with review checkpoints
- `finishing-a-development-branch` — Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
- `requesting-code-review` — Use when completing tasks, implementing major features, or before merging to verify work meets requirements
- `source-command-retro` — Close out work with a short retrospective and update project memory.
- `source-command-verify` — Run the read-only quality gate and tests, then summarize results.
- `subagent-driven-development` — Use when executing implementation plans with independent tasks in the current session
- `test-driven-development` — Use when implementing any feature or bugfix, before writing implementation code
- `ui-ux-pro-max` — UI/UX design intelligence for web and mobile. Includes 50+ styles, 161 color palettes, 57 font pairings, 161 product types, 99 UX guidelines, and 25 chart types across 10 stacks (React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui, and HTML/CSS). Actions: plan, build, create, design, implement, review, fix, improve, optimize, enhance, refactor, and check UI/UX code. Projects: website, landing page, dashboard, admin panel, e-commerce, SaaS, portfolio, blog, and mobile app. Elements: button, modal, navbar, sidebar, card, table, form, and chart. Styles: glassmorphism, claymorphism, minimalism, brutalism, neumorphism, bento grid, dark mode, responsive, skeuomorphism, and flat design. Topics: color systems, accessibility, animation, layout, typography, font pairing, spacing, interaction states, shadow, and gradient. Integrations: shadcn/ui MCP for component search and examples.
- `using-git-worktrees` — Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback
- `writing-clearly-and-concisely` — Apply Strunk's timeless writing rules to ANY prose humans will read—documentation, commit messages, error messages, explanations, reports, or UI text. Makes your writing clearer, stronger, and more professional.
- `writing-plans` — Use when you have a spec or requirements for a multi-step task, before touching code

Refresh this layout with `make sync-skills` (or `make check-sync` to verify it is current).
<!-- END GENERATED SKILLS -->

## Level 3 — Automation

- `.github/automation.md`

## Level 4 — Orchestration

- `.github/orchestration.md`

## Level 5 — Agents and SDLC

- `.github/agents/` — governed, tool-agnostic agent definitions.
- `.github/sdlc.md` — plan -> implement -> test -> document -> review, each gated by
  a `make` target.
- `.github/portability.md` — runtime/model tier abstraction and self-hosted fallback.

## Runtime Rules

- Use user language for interaction.
- Keep all code artifacts in English.
- Prefer Makefile and uv workflows.
- NEVER perform git commits, git pushes, or branch integrations automatically. Leave all changes unstaged so the user can commit them manually.
