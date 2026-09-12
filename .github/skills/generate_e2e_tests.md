---
name: generate_e2e_tests
description: Use when generating end-to-end tests for critical user, API, CLI, or service flows.
summary: End-to-end tests for a critical user, API, CLI or service flow
family: quality-testing-debugging
visibility: internal
profile: core
auto_trigger: true
maturity: stable
risk: writes-files
small_model_path: false
triggers:
  - end-to-end test
  - e2e
  - end to end
  - integration flow test
  - api flow test
  - cli flow test
  - critical flow
---

# Skill: generate_e2e_tests

## Purpose

Generate end-to-end tests that validate critical user or API flows.

## Required Input

- Target flow description.
- Entry point (API/CLI/service).
- Fixtures or test data assumptions.
- Success and failure criteria.

## Output Format

- Test file path under `tests/`.
- Scenario list (happy path + key edge paths).
- Execution command (`make test` or scoped pytest command).

## Execution Rules

1. Keep tests deterministic and isolated.
2. Avoid coupling tests to notebook artifacts.
3. Use clear test naming and English docstrings/comments.
