# Copilot Instructions (Template Governance Adapter)

## `local_model_32k` mode — read this first, it overrides everything below

When the task is a spike / prototype / vibe-coding session (the user mentions
`local_model_32k` or `LOCAL_AGENT.md`, or asks to build/fix step by step):

- Apply `LOCAL_AGENT.md` only. **Skip Levels 1-5 below** — no governance, no skill lookups.
- **These override the general guidance in this file:** do NOT "gather as much context as
  needed", do NOT "read large chunks", do NOT keep calling tools until fully done. Instead:
  one whole-file read, one targeted edit, one result line, then stop.
- **Never rewrite a whole file** and keep output small — a large response fails with
  "Response too long" and loses the turn. Fix one root cause per turn.
- **End each increment by telling the user to open a NEW chat** — long chats get auto-compacted
  and you lose the code state. Never output a "what's implemented / what's missing" summary; on
  resume, re-read only what the next increment needs.

Output is also capped at the gateway (`max_tokens`) so over-long responses fail fast by
design — see `docs/local-model-runtime-config.md`.

---

Use the following 4-level structure as the single source of truth:

## Level 1 — Governance

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

Always read and apply these files before generating code or plans.

## Level 2 — Operational Skills

Internal governed skills are the source of truth:

- `.github/skills/` (internal curated)
- `.github/skills-external/` (synced external/vendor)

Prefer internal curated skills when both define overlapping capabilities.

Claude Code has a generated native view at `.claude/skills/`, Antigravity has a generated native view at `.agents/skills/`, and OpenCode has a generated native view at `.opencode/skills/`. All three are refreshed with `make sync-skills`; each can also be refreshed individually with `make setup-claude-skills`, `make setup-antigravity-skills`, or `make setup-opencode-skills`. Copilot should continue to use `.github/skills/` and `.github/skills-external/` as inline instruction references.

<!-- BEGIN GENERATED SKILLS (managed by skills_sync; do not edit) -->
Read skills from `.github/skills/` (internal, wins on name conflicts) and `.github/skills-external/` (vendored). Full catalog (families, visibility, profiles): `docs/generated/skills-catalog.md`.

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

Each skill must:

- receive explicit input,
- produce structured output,
- comply with governance files.

## Level 3 — Real Automation

Prefer system-enforced quality over model-only behavior:

- strict lint rules
- CI checks
- structure enforcement
- PR bots

Automation policy reference:

- `.github/automation.md`

## Level 4 — Orchestration

Use explicit orchestration for complex tasks:

- plan-first requirement
- step-by-step execution
- mandatory diff review
- validation against automation
- no direct large generation without relevant skill invocation

Orchestration policy reference:

- `.github/orchestration.md`

## Level 5 — Agents and SDLC

- `.github/agents/` — governed, tool-agnostic agent definitions.
- `.github/sdlc.md` — lifecycle phases gated by `make` targets.
- `.github/portability.md` — model tier abstraction and self-hosted fallback design.

## Additional Rules

- Interact with user in the language used by the user.
- Keep all code artifacts in English.
- Prefer `Makefile` commands and `uv` workflow.
- When implementing and testing new changes, create or update documentation in `docs/`.
- NEVER perform git commits, git pushes, or branch integrations automatically. Leave all changes unstaged so the user can commit them manually (policy `git-actions`; an explicit user request in the session is the only override).
