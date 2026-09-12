# Claude Code Adapter

Use this repository-level structure as the canonical source of instructions.

## Governance

Always read and apply these files before generating code or plans:

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

## Operating playbook

How to work in this repository to produce high-quality, well-grounded changes. These
are defaults, not ceremony — scale them to the task. The full rationale and the
end-to-end loop live in `docs/agentic-workflow.md`.

### Ideal working loop

Use **Ground → Plan → Delegate → Verify → Compound** for all meaningful work. The
loop is mandatory as a mental model; the amount of ceremony must scale with task
size, risk, and reversibility.

#### Tiny changes

For typos, comments, one-line fixes, or obvious local edits:

- Read the target file before editing.
- Make the smallest safe change.
- Run the narrowest relevant check when one exists.
- Do not create ADRs, memory entries, or broad plans unless something non-obvious
  was learned.

#### Normal engineering tasks

For bugs, features, refactors, tests, docs with behavior impact, or multi-file
changes:

1. **Ground** — inspect relevant files, search usages, and read project memory when
   useful.
2. **Plan** — write a short phased plan before editing.
3. **Delegate** — use subagents when subtasks are independent.
4. **Verify** — run focused checks during the work and a final project gate before
   completion.
5. **Compound** — update memory or ADRs only for durable learnings or decisions.

#### Large or risky work

For architectural, cross-module, production, data, security, migration, or
hard-to-reverse work:

- Use explicit planning and phase boundaries.
- Prefer parallel research, review, implementation, and test subagents where tasks
  are independent.
- Require verification and review before declaring the work done.
- Record architectural decisions in `docs/adr/`.

Do not perform ceremony for its own sake. A typo does not need an ADR; a durable
architecture choice does.

1. **Ground before doing.** Read and search the relevant code before editing. Skim
   `memory/context.md` and `memory/learnings.md` for prior context. Explore first;
   blind edits cause rework.
2. **Plan multi-step work.** For anything beyond a trivial change, start with a
   `TodoWrite` plan and the `writing-plans` / `brainstorming` (or `brainstorm_quick`)
   skill. Complete one phase before the next.
3. **Delegate independent work in parallel.** When subtasks are independent, dispatch
   them to subagents concurrently (one message, multiple `Task` calls) per the
   `subagent-driven-development` skill. Use the governed agents in `.github/agents/`.
4. **Verify continuously.** Run `make test` (or focused `pytest`) after each
   substantive change, and close work with `make check` and the
   `requesting-code-review` skill. The `/verify` command bundles the gate.
5. **Compound knowledge.** When you finish a unit of work, record decisions in
   `docs/adr/` and durable learnings in `memory/`. Use `/adr` and `/retro`. Leave the
   repo's memory richer than you found it.
6. **Prefer CLI, load tools on demand.** Reach for `make` / `uv` / CLI over MCP where
   both work (leaner and reproducible). Use ToolSearch to load tool schemas on demand
   rather than assuming a tool is unavailable.
7. **Use the toolbelt before asking.** Before asking the user for operational or
   repository information, check whether an available MCP server, CLI, Make target,
   or local service can retrieve it directly. See `docs/claude-toolbelt.md`.
8. **Recover, don't thrash.** On an error, diagnose the cause before retrying; do not
   hammer the same file repeatedly. Get it right early rather than iterating blindly.
9. **Match the model to the task.** Use the planner / executor / fast tiers in
   `.github/portability.md`; offload routine sub-work to cheaper models and reserve
   the strongest model for planning and hard reasoning.

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
Skills are projected into `.claude/skills/`; governed sources: `.github/skills/` (internal, wins on name conflicts) and `.github/skills-external/` (vendored). Full catalog (families, visibility, profiles): `docs/generated/skills-catalog.md`.

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

## Automation

Prefer system-enforced quality over model-only behavior:

- Automation policy: `.github/automation.md`
- Local sequence: `make format` -> `make fix`; CI-safe gate: `make check`.
- CI is read-only (`make ci` = `make check` + `make check-sync` +
  `make check-docs-coverage`) — never relies on CI to format or fix.

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
- NEVER perform git commits, git pushes, or branch integrations automatically. Leave all changes unstaged so the user can commit them manually (policy `git-actions`; an explicit user request in the session is the only override).
