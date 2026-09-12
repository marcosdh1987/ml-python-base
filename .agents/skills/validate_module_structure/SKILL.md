---
name: validate_module_structure
description: Use when validating module placement, dependency direction, and structure against repository governance.
summary: Check module placement and dependency direction against governance
family: architecture-contracts
visibility: internal
profile: core
auto_trigger: true
maturity: stable
risk: read-only
small_model_path: false
triggers:
  - module placement
  - validate structure
  - dependency direction check
  - where should this module live
  - check the boundaries
---

# Skill: validate_module_structure

## Purpose

Validate module placement and dependency direction against governance rules.

## Required Input

- Module or package path(s) to validate.
- Expected layer classification.
- Optional known anti-patterns to check.

## Output Format

- Compliance checklist.
- Violations grouped by severity.
- Suggested minimal fixes.

## Execution Rules

1. Validate against `.github/architecture.md` and `.github/domain-boundaries.md`.
2. Prioritize architectural violations over style issues.
3. Keep recommendations actionable and minimal.
