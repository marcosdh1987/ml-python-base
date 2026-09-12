# ADR-0002: Layer the skills catalog with metadata, overlays and routing evals

- **Status:** Proposed
- **Date:** 2026-09-12
- **Deciders:** template maintainers (harness engineering)
- **Related:** ADR-0001; `docs/skills-guide.md`; `docs/skills-management.md`;
  `docs/skills-catalog-v3-audit.md`; `memory/learnings.md` (2026-08-14, weak-model
  front-loading)

## Context

The harness projected a flat list of 27 skills, identically, into every tool. Three
forces made that untenable:

1. **Cognitive and context cost.** A developer had to know 27 names; every model,
   including 32k self-hosted ones, read all 27 descriptions before doing anything.
2. **Conflicting triggers and duplicates.** The vendored `brainstorming` skill
   declared itself mandatory "before ANY creative work", neutralising the governed
   `brainstorm_quick`; two first-party skills (`source-command-verify/retro`)
   duplicated `verify_changes` / `retrospective`; retired names
   (`execute_engineering_task`, `create_use_case`, …) lingered in READMEs.
3. **Vendor steps that break policy.** Superpowers skills instruct `git commit`,
   `git push`, `git merge` and branch deletion. The repository forbids agents from
   doing that unasked, but the rule lived in only two of five adapters and nothing
   stopped the vendor text from being followed. Editing vendored files is not
   viable: the next sync overwrites them and a fork loses upstream fixes.

The existing engine (`skills_sync`, `adapters/registry.toml`, `skills-lock.json`,
`make sync-skills` / `check-sync`) is sound and must be extended, not replaced.

## Decision

We will layer the catalog on top of the existing engine:

- **Declarative metadata per skill** — `family`, `visibility`
  (`developer | internal | optional | hidden | legacy`), `profile`, `auto_trigger`,
  `maturity`, `risk`, `small_model_path`, `triggers`, `replacement`, `summary`.
  Internal skills author it in their frontmatter; vendored skills get a
  `[skill.<name>]` overlay in the registry. Overlay beats frontmatter beats defaults.
  Vocabularies (`families`, `profiles`) are declared once in `[catalog]` and
  validated on every sync.
- **Visibility drives projection.** `developer` skills are entrypoints (nine),
  listed by intent at the top of every adapter; `internal` primitives are listed
  compactly; `optional` specialists after them; `hidden` only when named; `legacy`
  never projected — adapters map the old name to its `replacement`. Retired
  skills whose files are deleted survive as `[alias.<name>]` metadata.
- **Projection-time overlays for vendored skills.** When a skill has a policy or an
  overridden `description`, its projected `SKILL.md` is generated (governed
  frontmatter, a short banner stating what takes precedence, vendor body verbatim).
  The vendor source, its lock hash and its licence record never change.
- **Policies as registry data.** `[policy.git-actions]` states the rule once, lists
  the skills it applies to, renders into every adapter and into each covered
  projection; a test fails if a vendored skill instructs a mutating git action
  without being covered, and `.claude/settings.json` asks before those commands.
- **One generated catalog** (`docs/generated/skills-catalog.md`) and one wiki-ready
  guide (`docs/skills-guide.md`); `make check-sync` fails on catalog drift so no
  hand-maintained skill list remains.
- **Routing evals.** Versioned scenarios (`tests/routing/scenarios.toml`) run in CI
  through a deterministic reference router built from the `triggers`; a live model
  eval is opt-in (`make routing-eval-live`).
- **Small-model path stays first-class.** `LOCAL_AGENT.md` and
  `plan_and_execute_feature`'s `local_model_32k` mode are untouched; the adapter
  block names the skills with `small_model_path: true` so the path reaches weak
  executors without a lookup.
- **`template_sync.protocol` becomes 2**, because adapter templates (governance
  path) now need catalog variables the protocol-1 engine (platform path) cannot
  supply.

## Consequences

Easier: a developer learns nine intents, not 27 names; every adapter block is about
19% smaller while carrying routing rules, policy and aliases; contradictory triggers
are gone; vendor git behaviour cannot bypass governance; docs cannot drift from the
catalog; routing is tested. Harder: downstream repositories must adopt the platform
upgrade (engine + registry blocks) before syncing protocol-2 governance — the
harness lab's `harness-sync-preview` blocks until they do; `.claude/skills/<name>/SKILL.md`
is a regular file rather than a symlink for overlaid skills, so tooling that
assumed "every native entry is a symlink" must branch on content instead. Risks
accepted: the deterministic router is a proxy for model behaviour (the live eval
exists for that reason); `triggers` need light curation when a skill's scope
changes.

## Alternatives considered

- **Edit vendored skills in place** — silent fork, overwritten by the next sync,
  loses upstream fixes; rejected.
- **Rely on instruction hierarchy** (adapter prose outranks skill text) — the
  audit showed weak models follow whatever they read last; rejected as the only
  mechanism.
- **Physically move skills into family folders** — high churn across five
  projections and every downstream repo for no runtime gain; metadata achieves
  the same discoverability.
- **A generic plugin/profile platform** — no consumer today; profiles as one value
  per skill are enough to group and drop capabilities.
- **A YAML dependency for frontmatter** — the subset skills use (scalars, quoted
  strings, inline and block lists) is parsed in 80 lines; no new dependency.
