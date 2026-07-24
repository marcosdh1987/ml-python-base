# Domain Boundaries

This document defines module and data boundaries for consistent generation.

## Repository Zones

- `src/`: production code only.
- `tests/`: automated tests.
- `notebooks/`: exploratory work and prototyping.

## Data Zones

- `data/raw/`: immutable source data (read-only for pipelines).
- `data/processed/`: transformed/feature-ready data.

Rules:

- Never overwrite raw data in-place.
- Write transformations to processed artifacts.

## Prompt and Agent Zones

- Prompt logic should live under `src/agent_rag/prompts/` when applicable.
- Keep prompt templates separate from execution/runtime code.

## Dependency Boundaries

- Domain/application modules should not depend directly on notebook code.
- Test helpers should not leak into production modules.
- Infrastructure concerns should stay out of domain core.

## Change Boundaries

When implementing tasks:

- Change only files related to the requested scope.
- Avoid cross-cutting refactors unless explicitly requested.

## Verification Gate

- For changed behavior, run the **narrowest relevant target test** first (a focused
  `pytest` selecting the affected test), then `make check` as the broader canonical
  gate. Syntax checks or manual reasoning only supplement executed tests — they
  never replace them.
- Record the exact command and its exit status before declaring the hypothesis
  confirmed or refuted.
- For stateful or edge-case behavior (e.g. game-over/restart or other state
  transitions), the verify step MUST include a deterministic recipe that forces the
  specific state transition and confirms recovery. Do not rely on a generic smoke
  input that never reaches the failure mode; treat this recipe as part of the
  normal verify step, not an optional extra.
- Advance to the next step only after the verification gate exits green.
- Do not substitute narrative assertions ("it should work", "this looks correct")
  for a formal, executed check result.
