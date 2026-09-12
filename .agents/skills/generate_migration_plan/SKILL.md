---
name: generate_migration_plan
description: Use when planning low-risk code, data, or architecture migrations with validation and rollback steps.
summary: Phased, reversible plan for a code, data or architecture migration, with rollback and checks
family: planning-execution
visibility: developer
profile: core
auto_trigger: true
maturity: stable
risk: read-only
small_model_path: false
triggers:
  - migration
  - migrate
  - rollback plan
  - schema change
  - data migration
  - upgrade path
  - move from
  - cut over
  - rollback
---

# Skill: generate_migration_plan

## Purpose

Create a migration plan for code, data, or architecture changes with low operational risk.

## Required Input

- Migration objective.
- Source state and target state.
- Compatibility constraints.
- Downtime and rollback constraints.

## Output Format

- Phase-by-phase migration steps.
- Preconditions and validation checks per phase.
- Rollback strategy.
- Post-migration verification checklist.

## Execution Rules

1. Prefer incremental and reversible steps.
2. Define clear checkpoints before irreversible operations.
3. Include lint/test/structure verification points.
