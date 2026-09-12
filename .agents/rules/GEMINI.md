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

If an internal governed skill and an external synced skill share the same name, prefer the internal governed skill. When skills overlap in purpose, follow the **Routing rules** in the generated block below (bounded change → `brainstorm_quick` or straight to `plan_and_execute_feature`; new subsystem or design-impacting change → `brainstorming`). If unsure which applies, state the chosen skill and why in the run trace.

<!-- BEGIN GENERATED SKILLS (managed by skills_sync; do not edit) -->
Skills are projected into `@.agents/skills/`; governed sources: `@.github/skills/` (internal, wins on name conflicts) and `@.github/skills-external/` (vendored). Full catalog (families, visibility, profiles): `@docs/generated/skills-catalog.md`.

**Start here — match the intent, then read that skill (9 entrypoints own every task):**

- start a project from this template → `bootstrap_project`
- explore a scoped idea or compare options → `brainstorm_quick` (no spec, no approval gate)
- design a new subsystem or a design-impacting change → `brainstorming` (written spec + user approval before code)
- implement a feature or an approved plan → `plan_and_execute_feature` (`mode: execute_only` when the plan already exists)
- fix a failing test, traceback or wrong behavior → `systematic_debugging`
- plan a code, data or architecture migration → `generate_migration_plan`
- check current facts (versions, APIs, releases) → `research_current_info`
- verify the work before calling it done → `verify_changes`
- review the finished diff → `requesting-code-review`

**Internal primitives (12)** — composed by the entrypoints; invoke one directly only when the task is exactly that step:

- `create_domain_contract` — Define a typed use case or repository interface with clean-architecture boundaries
- `executing-plans` — Execute a written plan in a separate session with review checkpoints (no subagents)
- `finishing-a-development-branch` — Close a finished branch: verify tests, then present merge / PR / keep / discard options to the user
- `generate_e2e_tests` — End-to-end tests for a critical user, API, CLI or service flow
- `generate_implementation_docs` — Write or update the `docs/` page for a completed change: what, why, how verified
- `refactor_to_clean_architecture` — Realign a module's dependency direction and boundaries, behavior preserved
- `retrospective` — Persist durable, non-obvious learnings into `memory/` and flag ADR-worthy decisions
- `subagent-driven-development` — Execute a plan with one fresh subagent per task and a two-stage review (spec, then quality)
- `test-driven-development` — Write the failing test first, watch it fail, then the minimal code to pass
- `using-git-worktrees` — Work in an isolated worktree: prefer the platform's native tool, fall back to git worktree
- `validate_module_structure` — Check module placement and dependency direction against governance
- `writing-plans` — Turn an approved spec into a bite-sized implementation plan with exact files, code and checks

**Optional / specialist (3)** — use one when the request is in its domain, even if no entrypoint fits:

- `create_mle_agent_package` (python-ml) — Spec and file plan for a pip-installable, provider-agnostic MLE agent package
- `ui-ux-pro-max` (frontend) — Any UI/UX request — landing pages, dashboards, components, CSS/Tailwind/React styling, palettes, typography, accessibility
- `writing-clearly-and-concisely` (core) — Apply Strunk's rules to prose humans will read: docs, messages, reports, UI text

**Routing rules:**

- Bounded, scoped change (a flag, a timeout, one function) → `brainstorm_quick` when options are unclear, otherwise straight to `plan_and_execute_feature`. New subsystem, significant design impact, or ambiguous architecture → `brainstorming` (written spec, user approval), then `writing-plans`.
- An approved plan or an already-scoped fix → `plan_and_execute_feature` with `mode: execute_only`; do not reopen design.
- A failing test, traceback, or unexpected behavior → `systematic_debugging` before any edit; `test-driven-development` for the regression test.
- Before declaring anything done → `verify_changes`. For a review of the finished diff → `requesting-code-review`.
- Skip a skill only when the user asks for a tiny edit; say which skill was skipped and why.

**Small or self-hosted model:** Follow `LOCAL_AGENT.md`: one root cause or one increment per turn, one or few files per step, edit never rewrite, declare `Target file / Expected change / Validation` before editing, run the validation command, then stop. Drive the work with `plan_and_execute_feature` in `mode: local_model_32k`. Skills with an explicit small-context mode: `brainstorm_quick`, `plan_and_execute_feature`, `systematic_debugging`, `verify_changes`.

**Policies** (override any skill step that contradicts them):

- **Git actions are recommendations:** Agents may recommend git actions and prepare commands, diffs, commit messages and PR text. They MUST NOT run `git commit`, `git push`, merge, rebase, or delete branches unless the user explicitly asks for that exact action in the current session; where a skill step says commit/push/merge, hand the prepared command to the user instead.

**Legacy names** (not projected; use the replacement): `create_repository_interface` → `create_domain_contract`; `create_use_case` → `create_domain_contract`; `execute_engineering_task` → `plan_and_execute_feature`; `source-command-retro` → `retrospective`; `source-command-verify` → `verify_changes`.

Refresh with `make sync-skills`; `make check-sync` verifies it is current.
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
- NEVER perform git commits, git pushes, or branch integrations automatically. Leave all changes unstaged so the user can commit them manually (policy `git-actions`; an explicit user request in the session is the only override).

## Operating discipline (Antigravity)

Follow the operating discipline and run-trace rules in @.github/sdlc.md. In short:

- **Follow the mandatory skill flow** for full features (brainstorm → plan → TDD →
  verify → review); do not jump straight to code. If you skip a skill, say why.
- **Minimize human interventions.** Inspect the repo, read files, run safe read-only
  commands, and make a reasonable assumption when the next step is low-risk. Ask only
  for destructive actions, secrets, ambiguous product decisions, or irreversible
  choices — with the exact blocker, what you tried, and 1-3 options.
- **Validate before claiming done** and report the exact commands and results. Never
  declare completion without them.
- **Stay inside the requested task/workspace directory** unless authorized otherwise.
- **Leave a run trace:** at the start, state files read, skills to use, edit boundary,
  and a short plan; at the end, a handoff (skills used, files changed, gates run +
  results, skipped validation + why, assumptions, human interventions).
