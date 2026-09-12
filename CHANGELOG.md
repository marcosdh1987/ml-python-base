# Changelog

All notable changes to this template are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/). Downstream projects adopt a release with
`make template-sync REF=vX.Y.Z` (see `docs/template-sync.md`).

## [1.0.0]

First MAJOR release: the skills catalog is reorganized, two duplicate skills are
removed, and `[template_sync].protocol` moves to **2**. Downstream repositories
must adopt the platform upgrade (the `skills_sync` engine plus the registry's
`[catalog]` blocks) before syncing protocol-2 governance — migration steps in
[`docs/skills-catalog-v3-audit.md`](docs/skills-catalog-v3-audit.md) §6.

### Added
- **Skills catalog v3** (`docs/skills-guide.md`, `docs/generated/skills-catalog.md`,
  ADR-0002). Every skill now carries catalog metadata — `family`, `visibility`
  (`developer | internal | optional | hidden | legacy`), `profile`, `auto_trigger`,
  `maturity`, `risk`, `small_model_path`, `triggers`, `replacement`, `summary` —
  authored in the frontmatter of internal skills and declared as `[skill.<name>]`
  overlays in `adapters/registry.toml` for vendored ones. The developer-facing
  catalog shrinks to nine intent-driven entrypoints; primitives and specialists
  remain available but no longer compete at the same level. The generated
  catalog document is written by `make sync-skills` and guarded by
  `make check-sync`; hand-maintained skill lists were removed from `README.md`,
  `.github/skills/README.md` and `docs/skills-management.md`.
- **Projection-time overlays and policies for vendored skills.** A skill with a
  registry `description` override or a policy gets a generated native `SKILL.md`
  (governed frontmatter + a short precedence banner + the vendor body verbatim);
  the vendor source, its lock hash and licence record stay untouched.
  `[policy.git-actions]` states once that agents may recommend and prepare git
  actions but MUST NOT commit, push, merge or delete branches unasked; it renders
  into every adapter and into the six covered Superpowers skills.
  `tests/skills_sync/test_policies.py` fails if a vendored skill instructs a
  mutating git action without coverage, and `.claude/settings.json` now asks
  before `git commit` / `push` / `merge` / `rebase` / branch deletion.
- **Routing evals.** `tests/routing/scenarios.toml` (30 versioned scenarios:
  positive, negative, overlap, legacy, small-model, specialist, hidden) run in CI
  through a deterministic reference router (`skills_sync.routing`); `make route
  PROMPT=…` explains one decision; `make routing-eval-live` (`scripts/routing_eval.py
  --live`) asks a real model the same questions, opt-in.
- Make targets `render-catalog`, `route`, `routing-eval`, `routing-eval-live`;
  engine subcommands `catalog` and `route`.
- **Tool-level enforcement of the `git-actions` policy.** The mutating command
  list lives once in `skills_sync.permissions` and is derived into every dialect
  a platform offers: Claude Code `permissions.ask`, an OpenCode
  `permission.bash` glob map (in `opencode.json` **and** in every generated
  `.opencode/agents/*.md` that may run shell), and VS Code
  `chat.tools.terminal.autoApprove` rules shipped as
  `.vscode/settings.recommended.json` for Copilot agent mode. `ask`, never
  `deny`, so an explicitly requested action still runs. Codex and Antigravity
  expose no per-command repository primitive and stay instruction-level;
  `docs/skills-guide.md` carries the matrix.
- **Four engine extension points, for downstream repositories that project a
  governed harness into a foreign root**: `linker.link_tool(..., strategy=)`,
  `linker.add_skills()` (copy without pruning the target's own view),
  `renderer.render_region/render_tool(..., template_root=)` and
  `cli.check_drift()` (the programmatic half of `check`). All four apply the
  catalog rules — legacy skills are still filtered, overlays are still written —
  and the overlay banner now names the governed path instead of raising when the
  source lives outside the projection root.

- **Test suite for the catalog, the policy and the routing** (`tests/skills_sync/test_catalog.py`, `test_overlay.py`, `test_policies.py`,
  `test_aliases.py`, `test_linker_extensions.py`, `test_frontmatter.py`, `tests/routing/`): 260 tests, up from 134.

### Changed
- **`brainstorming` no longer claims every creative task.** Its projected
  description is the governed one ("design-impacting work: new subsystem,
  significant architecture change, ambiguous requirements; bounded change →
  `brainstorm_quick`"); the routing rule is rendered in every adapter and the
  contradictory "choose the stricter one" prose in `.agents/rules/GEMINI.md` is
  gone.
- **Adapter skills block** redesigned for progressive disclosure: intents →
  primitives → optional → routing rules → small-model line → policies → legacy
  names. About 19% smaller than the flat 27-line list it replaces.
- The hand-written "NEVER perform git commits …" runtime rule now exists in all
  five adapters (it was missing from `CLAUDE.md`, `OPENCODE.md` and Copilot) and
  names the `git-actions` policy.
- `template_sync.protocol` is now **2**: adapter templates reference catalog
  metadata that only the v3 engine provides. Downstream repositories and the
  harness lab must adopt the platform upgrade (engine + registry `[catalog]`
  blocks) before syncing protocol-2 governance; `harness-sync-preview` blocks
  until they do.
- `make check-sync` additionally verifies generated overlay files, the absence of
  legacy entries in native views, and the generated catalog document.
- Catalog validation distinguishes hard errors (invalid vocabulary, legacy without
  a live replacement, alias collisions) from warnings (references to skills absent
  from the tree), so `make purge-external-skills` and partial downstream catalogs
  keep working.

### Removed
- `source-command-verify` and `source-command-retro` (first-party duplicates of
  `verify_changes` / `retrospective`, no consumer by name). Their names, and the
  earlier-retired `execute_engineering_task`, `create_use_case` and
  `create_repository_interface`, resolve through `[alias.*]` and are listed as
  legacy names in every adapter.

## [0.9.0]

### Changed
- feat: support internal skills as directories with executable helpers
- docs: document the two internal skill shapes

### Added
- **Internal skills may be folders.** An internal skill is no longer restricted
  to a flat `.github/skills/<name>.md`: it may be a `<name>/` directory with
  `SKILL.md` as its entry point and the scripts, templates or references it runs
  beside it. Shape and provenance are now independent, so an internally authored
  skill that ships a script no longer has to be smuggled into
  `.github/skills-external/`. `Skill.is_bundle` exposes the shape, and the linker
  branches on it instead of on `kind`.
- **Documented both skill shapes** (`docs/skills-management.md`,
  `.github/skills/README.md`, `CONTRIBUTING.md`): which layout to use, that the
  skill name comes from the file stem or folder name rather than the frontmatter,
  and that agents must call the governed path of a bundled script
  (`.github/skills/<name>/<script>`) — never a native copy, which is rebuilt on
  every sync.

### Fixed
- **Bundled scripts stay executable in copied views.** The copy strategy used by
  Antigravity replicated files with `shutil.copyfile`, which drops the mode bit,
  so a projected helper script was not runnable. It now uses `copy2`. Folder
  digests hash content only, so no manifest changes.

## [0.8.0]

Lessons back-ported from the organizational release of this template
(`xmartlabs/sdlc-ml-python-template` v1.0.0). Distribution and open-source
readiness work; no functional change to the harness.

### Added
- **Apache-2.0 licence and third-party attribution** (`LICENSE`, `NOTICE`): the
  repository previously carried no licence at all. `NOTICE` attributes the twelve
  skills vendored under `.github/skills-external/` — eight from
  [obra/superpowers](https://github.com/obra/superpowers) (MIT),
  [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT),
  [the-elements-of-style](https://github.com/obra/the-elements-of-style) (Public
  Domain), and two that are first-party. All inbound licences are compatible with
  Apache-2.0 outbound.
- **Declared provenance for vendored skills** (`adapters/registry.toml`,
  `skills_sync/config.py`, `skills_sync/lockfile.py`): a new `[external_skill]`
  table records `upstream` and `license` per skill, which `make sync-skills` now
  emits into every `skills-lock.json` entry. An undeclared skill renders as
  `UNKNOWN` and fails `make check`, so redistribution rights cannot silently
  lapse. Documented in `docs/skills-management.md`.
- **Community and governance files**: `SECURITY.md` (private vulnerability
  reporting), `CONTRIBUTING.md`, `.github/CODEOWNERS`,
  `.github/PULL_REQUEST_TEMPLATE.md`.

### Changed
- **CI runs with least privilege** (both workflows): added
  `permissions: contents: read`. Previously both inherited the repository
  default, which is often read/write on every scope.
- **Release manifests name the repository being released**
  (`scripts/harness_release.py`): the hardcoded `REPOSITORY` constant is now
  `repository()`, resolving from `HARNESS_RELEASE_REPOSITORY`, then the `origin`
  remote, then a default. Forks and downstream projects stamp their own slug.
- **README states what the repository is**: a template shipping an AI harness and
  a skills-projection engine, not an ML application. Repaired two `U+FFFD`
  corruptions, one of which had swallowed the "Dev Containers" heading into a
  code fence.
- **English-only code artifacts** (`pyproject.toml`, `.gitignore`,
  `.devcontainer/*`): translated the remaining Spanish comments and the project
  description, per the repository's own Runtime Rules.
- **`.env.example` flags the gateway aliases as an example topology** tied to one
  LiteLLM instance, so template consumers know to replace them.

### Removed
- **Dead application scaffolding** (`Makefile`, `README.md`): the
  `run-dev`/`run-api`/`run-question`/`run-interactive` targets and the Docker
  section referenced `api.py`, `main.py`, `Dockerfile.api`, `langgraph` and
  `uvicorn` — none of which exist in the template. The `run-batch-test` help
  lines pointed at targets that were never defined.
- **Stale `.gitignore` rules** from an unrelated earlier project (`webapp01/`,
  `dash/`, `milvus/`, `.promptflow/`, `.langgraph_api/`, notebook data paths).

## [0.7.0]

### Changed
- **Repo-agnostic debugging protocol and verification ladder** (`OPENCODE.md`,
  `AGENTS.md`, `.github/skills/systematic_debugging.md`,
  `.github/skills/verify_changes.md`, `.github/standards.md`, `LOCAL_AGENT.md`):
  the front-loaded adapter protocol no longer assumes this template's layout.
  Root pinning now derives the working root from `.git` / the failing test's path
  (template markers cited as the local example) and forbids retrying a failed
  path (one `find`, use its output). A new step requires reproducing the failure
  through the repo's own documented runner **before editing**, with a strict
  fallback ladder (documented gate/runner → `python -m pytest <test> -x` → direct
  execution of the real test functions) that explicitly bans self-written
  synthetic test scripts. Failed edits must be retried from a narrow ~10-line
  re-read with a smaller hunk instead of free-handed. Closure requires a green
  rerun of the exact reproduction command; after a failed verification the agent
  must change code or advance the diagnostic, never re-read unchanged code.
  `standards.md` Bug-Fix Discipline adds three matching **workflow failure
  signals** (synthetic-script verification, done-claims without an executed
  command, post-failure re-read/retry loops), `verify_changes` gains the runner
  ladder and an honest-closure rule, and `LOCAL_AGENT.md` ties the `✅ DONE`
  line to an executed validation command. Adapter copies remain byte-identical
  (HEP-2026-000, #47).
- **verify-gate plugin degrades safely outside the template**
  (`.opencode/plugin/verify-gate.ts`): the plugin now self-detects the template
  (`uv.lock` + `pyproject.toml` at the workspace root). In a foreign bench
  workspace it skips ruff (never reformats subject code), parse-checks edited
  files with plain `python -m py_compile`, suppresses exit-127 "command not
  found" noise (previously injected into the model's tool output as a fake
  `py_compile` error), and no longer runs `make check` on session idle — which
  previously could execute a foreign subject repo's Makefile (HEP-2026-000, #47).

### Added
- **Adapter-prose parity test** (`tests/governance/test_adapter_protocol_parity.py`):
  asserts the `## Debugging protocol` and `## Working loop` sections stay
  byte-identical between `OPENCODE.md` and `AGENTS.md` — the hand-written region
  that `make check-sync` cannot guard (HEP-2026-000, #47).
- **Foreign-workspace behavior documentation** (`docs/opencode-workflow.md`):
  how the harness behaves when mounted over a bench subject repo — root pinning,
  the runner preference ladder, verify-gate degradation, closure discipline.

## [0.6.0]

### Added
- **Front-loaded debugging protocol for opencode/codex adapters** (`OPENCODE.md`,
  `AGENTS.md`, `.github/skills/systematic_debugging.md`, `.github/standards.md`):
  a mandatory ordered checklist inserted before the skills block in both adapters —
  repo-root confirmation before any read/edit, open-the-evidence grounding,
  exact-failure restatement (exception, operands, call site), one-hypothesis-at-a-time
  probing with a stop-and-reframe rule, a parse/compile gate after every edit batch,
  targeted-test verification with an immediate lightest-executable fallback when the
  preferred runner is unavailable, and an incremental-edit rule. Includes a "Do not"
  section clarifying that `systematic_debugging` is a workflow to follow, not an agent
  to invoke. The canonical loop lives in the skill and `standards.md` Bug-Fix
  Discipline; the adapter copies are byte-identical (HEP-2026-000, #43).
- **`make check-docs-coverage` — docs-coverage gate, now local and in CI**
  (`Makefile`, `.github/workflows/docs-quality-guardrails.yml`,
  `.github/automation.md`): the PR rule "changes in `src/` or `tests/` require at
  least one updated file in `docs/`" previously lived only in the workflow YAML, so
  a green local `make ci` could still fail CI. The logic now lives once in the
  Makefile (`ci` includes it; the workflow calls the same target with
  `DOCS_BASE_REF=FETCH_HEAD`), diffing merge-base against the working tree so
  uncommitted changes count locally.

### Fixed
- **Release-flow tests failed on CI runners with no git identity**
  (`tests/harness_release/test_harness_release.py`): the publish tests execute a
  real `git tag -a` via the script under test, which inherits the process
  environment; fixtures now persist `user.name`/`user.email` in each temp repo's
  local config (`_configure_identity`) instead of relying on env-var identity that
  only covered the tests' own git calls. Reproduction recipe documented in
  `docs/harness-release-lifecycle.md`.

## [0.5.0]

### Added
- **`bootstrap_company_brain` skill** (`.github/skills/bootstrap_company_brain.md`):
  guides the interview-and-mine process that instantiates the company-brain template for
  a new organization — filling domain, glossary, conventions, architecture, and ownership
  from real sources (repos, docs, team interviews) and replacing every `_PENDIENTE_`
  marker with verified content. Companion guide: `docs/company-brain.md`.
- **`source-command-retro` and `source-command-verify` external skills**
  (`.github/skills-external/`): the `/retro` and `/verify` close-out and quality-gate
  loops projected as synced skills, so they are available in every supported tool rather
  than only as Claude Code slash commands.
- **Local-model Mac setup guide** (`docs/local-model-mac-setup.md`): the install path
  from a fresh clone to `make opencode` running against a self-hosted model — LM Studio,
  a local LiteLLM gateway, an honest memory budget for 16 GB / 24 GB machines, the
  environment-variable contract, and which knob is owned by the server, the gateway card,
  or `.env`. Complements the tuning levers in `docs/local-model-runtime-config.md`
  instead of duplicating them; both docs now cross-link.
- **`gateway/config.example.yaml`**: versioned LiteLLM gateway template carrying the
  output cap, temperature, repetition penalty, and timeouts as configuration rather than
  prose. The documented launch command pins `fastapi==0.140.0` — `litellm[proxy]` declares
  `fastapi>=0.136.3,<1.0` but imports `get_flat_dependant`, removed during the 0.140 patch
  series, so an unpinned install dies at startup. The real config (`gateway/config.yaml`)
  is git-ignored.

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
