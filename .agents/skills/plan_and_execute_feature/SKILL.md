---
name: plan_and_execute_feature
description: Use when delivering a feature through explicit planning, phased execution, validation, and governed handoff — or when implementing/fixing already-scoped engineering work via the execute_only mode.
---

# Skill: plan_and_execute_feature

## Purpose

Deliver a feature through explicit orchestration phases with architecture-safe execution.

## Mode

- `mode: full` (default) — run all five phases below, from planning to validation.
- `mode: execute_only` — a plan is already approved; skip Phases 1-2 and enter directly
  at Phase 4 (Execution), then Phase 5 (Validation). Use this for implementing a feature,
  fixing a bug, or executing scoped engineering work through governed orchestration
  instead of ad-hoc generation.

## Required Input

- Feature request.
- Business outcome.
- Affected modules and boundaries.
- Non-functional requirements (performance, security, observability).
- Test expectations.
- Optional `mode` (`full` | `execute_only`). For `execute_only`: the approved plan,
  scope constraints (files/modules in and out of scope), and acceptance criteria.

## Output Format

- Phase report (1 to 5).
- Approved implementation plan.
- Selected skills map.
- Code/test/doc change summary.
- Validation checklist with pass/fail evidence.

## Phases

### Phase 1 - Planning

- Clarify scope, assumptions, and acceptance criteria.
- Build a step-by-step implementation plan.

### Phase 2 - Architecture Validation

- Validate intended changes against:
  - `.github/architecture.md`
  - `.github/domain-boundaries.md`
- Adjust plan to preserve dependency direction and module placement.

### Phase 3 - Skill Selection

- Select internal operational skills needed for execution.
- Define invocation order and dependencies between skills.

### Phase 4 - Execution

- Implement changes following selected skills and plan order.
- Keep modifications scoped and documented.

### Phase 5 - Validation

- Validate against `.github/automation.md` and `.github/orchestration.md`.
- Review diffs, run required checks, and produce final summary.

## Execution Rules

1. Internal skills have precedence over external synced skills.
2. In `mode: full`, no direct implementation without completing Phase 1 and Phase 2.
3. Prefer minimal file churn and strict scope boundaries.
4. Include tests and `docs/` updates when behavior changes.
5. Escalate blockers with explicit assumptions and next actions.
6. Report open risks and deferred items explicitly.
