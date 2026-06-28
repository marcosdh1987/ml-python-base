# Changelog

All notable changes to this template are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/). Downstream projects adopt a release with
`make template-sync REF=vX.Y.Z` (see `docs/template-sync.md`).

## [0.2.0]

### Added
- **Selective governance sync**: `make template-sync [REF=vX.Y.Z] [TOOL=...] [PREVIEW=1]`
  pulls only the governance layer (skills, agents, governance docs, adapter templates)
  from a tag/branch and regenerates adapters — without touching code, `Makefile`, or data.
  Records the synced version in `.template-version` (`scripts/template_sync.py`).
- **Release flow**: `make template-release VERSION=X.Y.Z` (semver tags + this CHANGELOG).
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
