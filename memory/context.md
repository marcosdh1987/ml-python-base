# Current context

> Living snapshot of where the project is right now. Update at the start and end of
> a working session. Keep it short — archive stale items to `learnings.md` or delete.

## Project

- _Replace this section when you bootstrap a new project from the template_
  (`make init NAME=...`). Describe the project's purpose in one or two sentences.

## Active focus

- Skills catalog v3 (2026-09-12): layered catalog (9 developer entrypoints, 12
  primitives, 3 optional, 1 hidden, 5 legacy names), registry overlays + `git-actions`
  policy for vendored skills, generated `docs/generated/skills-catalog.md`, routing
  evals in `tests/routing/`. Protocol bumped to 2. Pending: human review + commit,
  release, and the harness lab's platform upgrade (merge of the engine diff +
  `registry=` in its ablation path). See `docs/skills-catalog-v3-audit.md`.
- Hardening pass closed (2026-09-12): git policy enforced at tool level on Claude
  Code and OpenCode (opt-in for Copilot; Codex and Antigravity have no primitive),
  four engine extension points upstreamed, and the lab migrated to protocol v2
  with its full suite green (1917 passed).

## Constraints & decisions in force

- _Hard constraints (stack, deadlines, non-functional requirements) and pointers to
  the ADRs that record the major decisions (`docs/adr/`)._

## Open threads / next steps

- Run a lab regression suite (`harness-regression-v1`) against the v3 release once
  tagged, to compare skill-consulted attribution before/after on real runs.
- Consider OpenCode `permission` rules for git mutations (mirror of the Claude
  `ask` list) once headless-run behaviour under "ask" is confirmed in the lab.
- `ml-langchain-agent` still ships the retired skills locally; its next template sync
  needs the same platform upgrade path as the lab.
