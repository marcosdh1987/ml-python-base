# Copilot Instructions (Template Governance Adapter)

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

Core internal skills:

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

## Additional Rules

- Interact with user in the language used by the user.
- Keep all code artifacts in English.
- Prefer `Makefile` commands and `uv` workflow.
- When implementing and testing new changes, create or update documentation in `docs/`.
