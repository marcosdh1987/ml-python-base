# Architecture Governance

This document defines the architectural frame for AI-assisted code generation.

## Core Principles

- Follow SRP (Single Responsibility Principle) for modules and classes.
- Keep business logic separated from infrastructure and configuration.
- Prefer explicit contracts (interfaces/protocols, typed boundaries).
- Avoid over-engineering; split modules only when lifecycle/responsibility differs.

## Preferred Layering

Use a simple, practical clean architecture style:

1. Domain layer: entities, value objects, core rules.
2. Application layer: use cases and orchestration.
3. Infrastructure layer: framework, I/O, DB, APIs, providers.

Rules:

- Domain must not depend on infrastructure.
- Application can depend on domain abstractions.
- Infrastructure depends on domain/application contracts.

## Python Structure Guidance

- Production code in `src/`.
- Tests in `tests/`.
- Exploration only in `notebooks/`.
- Prompts managed under `src/agent_rag/prompts/` when present.

## Decision Policy

When a generation request is ambiguous:

- Choose the simplest architecture-compatible solution.
- Preserve existing project style and naming.
- Minimize file churn and unrelated refactors.

## First-Pass Discipline

Before generating code or a plan for any non-trivial task:

1. Read the three core governance files in one pass, then the repository memory:
   - `.github/architecture.md`
   - `.github/standards.md`
   - `.github/domain-boundaries.md`
   - `memory/context.md` and `memory/learnings.md` (prior context and gotchas)

   This governance-and-memory read is mandatory and must happen before the first
   edit, not after it.
2. Write a short plan (one to three sentences) before touching any file. It MUST
   state: the intended fix or root cause, the specific files or symbols to inspect
   or modify, and the exact verification step — the target test or command that
   will confirm the change.
3. Do not begin editing files until the plan is written.
4. Re-read a governance or memory file only if the plan changes. Repeated reads of
   the same file without a plan update are a **workflow failure signal** — a sign
   that the agent is thrashing rather than progressing. When this occurs, stop,
   revise the plan, and proceed with a fresh targeted action.
