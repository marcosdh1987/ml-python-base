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
Skills are projected into `.codex/skills/`; governed sources: `.github/skills/` (internal, wins on name conflicts) and `.github/skills-external/` (vendored). Full catalog (families, visibility, profiles): `docs/generated/skills-catalog.md`.

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
- NEVER perform git commits, git pushes, or branch integrations automatically. Leave all changes unstaged so the user can commit them manually (policy `git-actions`; an explicit user request in the session is the only override).
