# Changelog

All notable changes to this template are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/). Downstream projects adopt a release with
`make template-sync REF=vX.Y.Z` (see `docs/template-sync.md`).

## [0.4.0]

### Added
- **Subagent handoff contract** (`.github/orchestration.md`): delegation is a closed
  loop — bound a discrete subproblem, delegate it, receive an explicit inspectable
  result, and merge it into the plan before advancing. Task-create/task-update activity
  is bookkeeping, not delegation; includes positive/negative examples and the degraded
  runtime fallback (HEP-2026-000, #37, PR #38).
- **Resumable execution and checkpointing** (`.github/orchestration.md`): checkpoint
  each verified milestone (milestone, plan position, green gates); resume from the last
  confirmed checkpoint after a session or transport drop; a checkpoint is valid only
  once its gate is green, and unrecorded progress is re-verified on resume.
- **Operating discipline rules 10–11** (`.github/sdlc.md`): delegate-as-closed-loop and
  checkpoint-verified-milestones, plus run-trace anchors — a per-phase checkpoint line
  (the resume anchor) and a per-delegation subproblem → result → merge record.
- **`make new-version [VERSION=X.Y.Z]`** — Step 2 of the release flow in one command:
  writes the version into `pyproject.toml`, scaffolds the `## [X.Y.Z]` CHANGELOG section
  from the commit subjects since the last tag, refreshes `uv.lock`, and prints the
  branch/commit/PR commands (`prepare` subcommand in `scripts/harness_release.py`).
  File-mutating but git-untouched; refuses non-increasing versions, existing tags, and
  duplicate CHANGELOG sections.

## [0.3.0]

### Added
- **First-pass discipline** (`.github/architecture.md`): a mandatory governance and
  memory read, followed by an explicit written plan — intended fix, files or symbols
  in scope, and the exact verification command — before the first edit. Repeated
  reads of the same file without a plan update are a workflow failure signal.
- **Verification gate** (`.github/domain-boundaries.md`): the narrowest relevant
  target test runs before `make check`; stateful and edge-case behavior requires a
  deterministic recipe that forces the transition. Narrative assertions never
  substitute for an executed check.
- **Retry and malformed-command policy** (`.github/standards.md`): one run per
  hypothesis, diagnose before re-running, and never retry a malformed command as-is.
- **Bug-fix discipline** (`.github/standards.md`): the explicit reproduce → isolate →
  hypothesize → fix → verify loop, carried by the `systematic_debugging` skill.
- **Branch finishing scope rule** (`.github/standards.md`): lateral setup work during
  branch finishing is a scope leak and is deferred or raised separately.
- **Release discipline** (`.github/standards.md`): the tag is the last step, never the
  first; a published tag is immutable; the files define the version and the tag only
  records it. Includes the recovery path for a tag created too early, so an agent
  driving a release cannot invert the order.
- README: a preflight troubleshooting table mapping every failure code
  (`version_mismatch`, `changelog_missing`, `tag_exists`, `dirty_tree`,
  `platform_change`, `invalid_semver`) to its cause and fix, plus the `tag_exists`
  recovery procedure.
- `docs/harness-release-lifecycle.md`: a "Recovering from a premature tag" section, an
  explicit note that pre-release (`-rc.N`) tags are outside the contract, and the rule
  that the version bump always trips `platform_change` — so `ALLOW_PLATFORM=1` is
  justified only when `pyproject.toml` and `uv.lock` are the entire platform delta.

### Changed
- The pre-finalization checklist now requires the focused target test to have run and
  passed, not just "relevant quality checks".
- README command table: the release row no longer advertises the deprecated
  `make template-release` as the way to tag; it lists the `harness-*` targets and marks
  `template-release` as deprecated.

## [0.2.1]

### Added
- `make version` — prints the `pyproject.toml` version (source of truth), the latest
  published tag, and whether a release is pending.
- `make harness-change-summary` now prints the concrete next version
  (`current → next`), not just the SemVer bump type.

### Changed
- Release manifests are written to the git-ignored `dist/` so the asset (which carries
  a self-referential commit SHA) is never accidentally committed.
- README: clearer, numbered "cut a release" flow with a concrete version example and a
  "what goes where" table; the deprecated `make template-release` points to it.

## [0.2.0]

### Added
- **Selective governance sync**: `make template-sync [REF=vX.Y.Z] [TOOL=...] [PREVIEW=1]`
  pulls only the governance layer (skills, agents, governance docs, adapter templates)
  from a tag/branch and regenerates adapters — without touching code, `Makefile`, or data.
  Records the synced version in `.template-version` (`scripts/template_sync.py`).
- **Traceable release contract**: read-only preflight and manifest tooling
  (`scripts/harness_release.py`, `make/harness.mk`, `schemas/harness-release-v1.schema.json`).
  `make harness-release-check VERSION=X.Y.Z` validates SemVer, version/changelog
  agreement, tag collision, a clean tree, governance-vs-platform classification, and
  provenance; `make harness-release VERSION=X.Y.Z` prints the exact manual tag/publish
  commands; `make harness-release-manifest` generates the release asset after tagging.
  Tagging, pushing, and GitHub Release publication stay manual. A structured
  `harness-improvement` issue form and a read-only `release-check` workflow accompany it.
- Governance run-trace and operating-discipline rules in `.github/sdlc.md` (mandatory SDLC
  skill flow, validate-before-done, minimize human interventions, task-scope confinement,
  start/end run trace).

### Changed
- `.github/skills/verify_changes.md`: required auditable output (manual checks, remaining
  risks, ready-for-review).
- `.github/skills/plan_and_execute_feature.md`: publish a visible plan before editing;
  execute in small checkpoints.
- `.agents/rules/GEMINI.md`: surface the operating discipline for Antigravity and clarify
  brainstorming vs brainstorm_quick vs plan_and_execute_feature precedence.

## [0.1.0]

### Added
- Initial template: governed `.github/` skills/agents, multi-tool adapters
  (Claude, OpenCode, Antigravity, Codex, Copilot), `skills_sync` engine, `make init`
  bootstrap, and full-repo template sync (`template-sync-merge` / `-rebase`).
