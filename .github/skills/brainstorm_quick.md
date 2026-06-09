---
name: brainstorm_quick
description: Use for fast, lightweight ideation at the start of a feature — diverge on a few options, weigh trade-offs, converge on a recommendation. For the full design-gate workflow use the external `brainstorming` skill instead.
---

# Skill: brainstorm_quick

## Purpose

Explore a problem space quickly before any plan or code exists. A lightweight,
governance-aligned alternative to the heavier external `brainstorming` skill: no
mandatory design document, no hard gate — just diverge, weigh, and converge so the
`plan_and_execute_feature` skill can turn the chosen direction into an explicit plan.

## Required Input

- Problem statement or feature idea (may be rough or ambiguous).
- Known constraints (deadlines, stack, non-functional requirements).
- Optional: prior attempts, hard requirements, things explicitly out of scope.

## Output Format

- Restated problem and the assumptions being made.
- Open questions for the user (ask the most decision-changing ones first).
- 2-4 distinct candidate approaches, each with trade-offs (effort, risk, fit).
- A recommended direction with rationale.
- A short handoff note to `plan_and_execute_feature`.

## Execution Rules

1. Diverge before converging: do not settle on one option until alternatives exist.
2. Ask clarifying questions when the input is ambiguous — do not invent requirements.
3. Challenge assumptions explicitly and call out unknowns and risks.
4. Stay within governance: `.github/architecture.md`, `.github/standards.md`,
   `.github/domain-boundaries.md`.
5. Do not write production code in this phase — output ideas, options, and a
   recommendation only.
6. Keep all artifacts in English.
