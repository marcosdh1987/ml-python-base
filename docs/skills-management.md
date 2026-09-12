# Skills Management

Engine reference for the skills system. The developer-facing explanation (what a
skill is, how to pick one, how to add or retire one) is
[`docs/skills-guide.md`](skills-guide.md); the generated inventory is
[`docs/generated/skills-catalog.md`](generated/skills-catalog.md).

## Engine overview

Skill/adapter/agent projection is handled by a single declarative engine —
`src/ml_python_base/skills_sync` — driven by the registry at
`adapters/registry.toml`. **Adding a new AI tool is one `[[tool]]` entry** in that
registry (plus a Jinja2 template under `adapters/templates/`); no Makefile edit is
needed. The Makefile targets are thin wrappers:

| Target | Engine command | Purpose |
|---|---|---|
| `make setup-claude-skills` | `link --tool claude` | Symlink native Claude skills |
| `make setup-opencode-skills` | `link --tool opencode` | Symlink native OpenCode skills |
| `make setup-antigravity-skills` | `link --tool antigravity` | Copy native Antigravity skills + manifest |
| `make render-adapters` | `render` | Regenerate the managed skill region in each adapter |
| `make render-catalog` | `catalog` | Regenerate `docs/generated/skills-catalog.md` |
| `make sync-agents` | `agents` | Project governed agents into native formats |
| `make sync-skills` | `sync` | ingest + link + agents + render + catalog (one-shot) |
| `make check-sync` | `check` | Fail if any generated artifact is stale (CI gate) |
| `make route PROMPT=…` | `route` | Route one request through the catalog (deterministic) |
| `make routing-eval` | — (pytest) | Deterministic routing scenarios, `tests/routing/` |
| `make routing-eval-live` | — (script) | Opt-in live routing eval against a real model |
| `make purge-external-skills` | `purge` | Reset external skills + native views |

Two skill sources:

- Internal/governed skills: `.github/skills/` (flat `<name>.md` or `<name>/SKILL.md`
  bundle — see "Internal skill shapes").
- External vendored skills: `.github/skills-external/<name>/` (always bundles),
  ingested from ad-hoc installs under `.agents/skills/` (fallback `.agent/skills/`).

Native views are generated per tool: `.claude/skills/`, `.opencode/skills/`,
`.codex/skills/` (symlinks) and `.agents/skills/` (copies + hidden manifest).
Governed folders remain the source of truth.

## Catalog metadata

Every skill carries catalog metadata. Internal skills declare it in their own
frontmatter; vendored skills, which cannot be edited, get it from a
`[skill.<name>]` overlay in the registry. Precedence per field: **overlay >
frontmatter > default**. Every field has a default, so a skill without metadata
still projects as an `internal` primitive of family `unclassified`.

| Key | Values | Default | Meaning |
|---|---|---|---|
| `family` | one of `[catalog].families` (or `unclassified`) | `unclassified` | what the skill is about |
| `visibility` | `developer` · `internal` · `optional` · `hidden` · `legacy` | `internal` | who it is for and whether it competes in discovery |
| `profile` | one of `[catalog].profiles` | `core` | which kind of project needs it |
| `auto_trigger` | bool | `true` | the model may select it from its description alone |
| `maturity` | `stable` · `experimental` · `deprecated` | `stable` | `deprecated` requires `visibility: legacy` |
| `risk` | `read-only` · `writes-files` · `git-mutating` · `network` | `writes-files` | side-effect class |
| `small_model_path` | bool | `false` | the skill documents a small-context mode; named in the adapters' small-model line |
| `triggers` | list of phrases | `[]` | matched by the deterministic router and shown in the catalog |
| `replacement` | skill name | `""` | required for `legacy` |
| `summary` | ≤ 140 chars | first sentence of `description` | the one-liner adapters show |
| `description` | overlay only | — | replaces the vendor trigger in the projected `SKILL.md` |

Visibility drives projection:

| Visibility | Adapter block | Native view |
|---|---|---|
| `developer` | intent line at the top | projected |
| `internal` | compact primitives list | projected |
| `optional` | specialist list, tagged with its profile | projected |
| `hidden` | not listed | projected (usable when named) |
| `legacy` | `old → replacement` line only | **not projected**; stale native entries are removed |

`[catalog]` also declares `output` (the generated catalog path), `routing_rules`
(prose bullets rendered into every adapter; backticked names must be live skills)
and `small_model_note` (the small-model line). `[[intent]]` entries feed the
"I want to… → skill" table; each must point at a `developer` skill.

Validation runs on every `sync`, `link`, `render`, `catalog` and `check`:
invalid vocabulary, a `legacy` skill without a live replacement, an alias that
collides with a live skill or an intent that points at a hidden skill are hard
errors. References to skills that are simply absent from the tree (an overlay or
policy for a purged external skill) are warnings, so a downstream repository that
carries a subset of the catalog still syncs. `tests/skills_sync/test_catalog.py`
asserts the committed repository has neither.

## Overlays and policies

A vendored skill is projected verbatim **unless** a registry overlay overrides its
`description` or a policy applies to it. Then the projected `SKILL.md` (in every
native view, symlink and copy alike) is a generated file:

```
---
name: brainstorming
description: "<governed description>"
---

> **Governed overlay — read first.** Projected by `skills_sync` from
> `.github/skills-external/brainstorming/SKILL.md` (vendored, unmodified).
> Repository policy takes precedence over any step below that contradicts it:
> - **Git actions are recommendations:** …
> - **Routing:** use this skill only when its governed trigger applies — …

<vendor body, byte-for-byte>
```

Other files of the bundle stay symlinked/copied. The vendor source, its hash in
`skills-lock.json` and its `NOTICE` entry do not change — the overlay is a
projection, not a fork. `make check-sync` compares each generated `SKILL.md`
(symlink tools) or the folder hash (Antigravity) against what the engine would
produce.

Policies are declared once:

```toml
[policy.git-actions]
title = "Git actions are recommendations"
summary = "Agents may recommend git actions … MUST NOT run `git commit`, `git push`, merge … unless the user explicitly asks …"
doc = ".github/standards.md"
applies_to = ["brainstorming", "executing-plans", "finishing-a-development-branch",
              "subagent-driven-development", "using-git-worktrees", "writing-plans"]
```

and rendered into every adapter's **Policies** section. `tests/skills_sync/test_policies.py`
fails when a vendored skill instructs a mutating git action (`git commit`,
`git push`, `git merge`, `gh pr create`, …) without being in `applies_to`, when a
covered skill's projected file lacks the banner, when an adapter lacks the policy,
and when `.claude/settings.json` does not ask before those commands.

## Legacy names

Retired names resolve without a duplicate skill competing in discovery:

- a skill kept on disk with `visibility: legacy` + `replacement`, or
- a deleted skill with an `[alias.<name>] replacement = "…"` entry.

Both render in the adapters' **Legacy names** line and in the catalog's "Legacy
names" table. `catalog.resolve_name()` follows chains; the router treats a legacy
name in a prompt as an explicit request for the replacement.

## Generated catalog

`make sync-skills` writes `docs/generated/skills-catalog.md` from
`adapters/templates/skills_catalog.md.j2`: the intent table, entrypoints,
primitives, optional, hidden, legacy names, routing rules, policies, the
small-model path, families, profiles, a full attribute table and the trigger
phrases. It is deterministic (no timestamps) and `make check-sync` fails when it
is stale, so README and wiki pages link to it instead of repeating lists.

## Routing evals

`tests/routing/scenarios.toml` holds versioned scenarios (`prompt`,
`expected_family`, `expected_skills`, `forbidden_skills`, optional `expected_mode`,
`reason`, tags). `tests/routing/test_routing.py` runs them through
`skills_sync.routing.route()` — a deterministic router that scores each skill's
`triggers` against the prompt, resolves legacy names, detects `execute_only` /
`local_model_32k` from phrase patterns and breaks ties by visibility rank — and
guards structural invariants: every entrypoint is exercised, every legacy name
resolves, routing rules name only live skills, small-model scenarios land on
skills with a small-model path, and the developer catalog is materially smaller
than the discoverable set. They run inside `make check`.

`scripts/routing_eval.py --live` (`make routing-eval-live`) asks a real model
(`claude -p` or `opencode run`) the same questions given only the adapter block,
and prints pass/fail per scenario. It is opt-in: it costs tokens and is not
deterministic. `--adapter` accepts any adapter file, including a saved older one,
for before/after comparisons.

## Internal skill shapes

A skill is either only prose, or prose plus the files it runs. Both shapes live in
`.github/skills/`, and the engine discovers them uniformly:

| The skill is… | On disk | `Skill.is_bundle` |
|---|---|---|
| A single `.md`, no helper files | `.github/skills/<name>.md` | `False` |
| Prose plus scripts, templates or references | `.github/skills/<name>/SKILL.md` with the helpers beside it | `True` |

The skill **name** comes from the file stem or the folder name, never from the
frontmatter. A folder without `SKILL.md` is not a skill and is skipped silently.
Internal skills sort by name, then external ones.

Projection covers both shapes: symlink tools (Claude Code, OpenCode, Codex) get
`SKILL.md` linked for a flat skill and one link per top-level entry for a bundle;
the copy tool (Antigravity) copies the tree with `shutil.copy2`, preserving the
executable bit. When a skill invokes a bundled script, point the agent at the
**governed** path (`.github/skills/<name>/<script>`), never at a native copy.

## Ideation routing: `brainstorm_quick` vs `brainstorming`

Two ideation skills coexist on purpose:

| Situation | Skill | Why |
|---|---|---|
| Scoped feature, bounded change, quick option comparison | `brainstorm_quick` (internal) | Diverge → weigh → converge → hand off to `plan_and_execute_feature`. Nothing persisted, no gate. |
| New subsystem, significant design impact, ambiguous architecture | `brainstorming` (external) | Written spec under `docs/`, explicit user approval, then `writing-plans`. |

The vendor's trigger ("you MUST use this before ANY creative work") is replaced in
projection by the governed description declared in `[skill.brainstorming]`, and
the same rule is one of the `routing_rules` every adapter renders. Caveats of the
vendored skill: its optional visual companion needs Node.js (text fallback
exists), and it references siblings with the `superpowers:` prefix — the same
skills are available here without it.

## Sync external skills to governed layout

```bash
npx skills add https://github.com/wshobson/agents --skill langchain-architecture
make sync-skills
```

`sync` (1) ingests `.agents/skills/` (fallback `.agent/skills/`) into
`.github/skills-external/<name>/`, skipping folders without `SKILL.md` and copies
that match the Antigravity manifest; (2) regenerates `skills-lock.json` (hash,
timestamp, upstream, licence); (3) removes the legacy `.agent/skills/`; (4) rebuilds
every native view, applying visibility and overlays; (5) projects governed agents;
(6) regenerates the adapter regions; (7) regenerates the catalog document.

## Provenance of vendored skills

Everything under `.github/skills-external/` is third-party content this repository
**redistributes**. Every vendored skill must declare where it came from and under
what terms in the `[external_skill]` table of `adapters/registry.toml`:

```toml
[external_skill.brainstorming]
upstream = "https://github.com/obra/superpowers"
license = "MIT"
```

`make sync-skills` copies those fields into each `skills-lock.json` entry. A skill
with no registry entry renders as `"UNKNOWN"` and `make check` fails
(`tests/skills_sync/test_config.py`). When you add an external skill: verify the
actual `LICENSE`, add the registry entry, add attribution to `NOTICE`, add a
`[skill.<name>]` overlay for its catalog metadata, run `make sync-skills` and
`make check`. If you cannot establish the licence, do not vendor the skill.

## Adapter skill regions and the drift gate

Each adapter file carries a machine-managed block between sentinels:

```
<!-- BEGIN GENERATED SKILLS (managed by skills_sync; do not edit) -->
...generated block...
<!-- END GENERATED SKILLS -->
```

Only that block is generated; the surrounding governance prose stays hand-written.
`make check-sync` fails if any adapter region, native view (generated overlay file
or a stale legacy entry), manifest, lock file, projected agent or the generated
catalog is stale relative to the governed sources. Fix drift with
`make sync-skills`.

Adapter templates are a governance path but the engine is a platform path. A
template that references new catalog variables therefore needs the matching
engine, which is why `[template_sync].protocol` is `2` for catalog v3: a
downstream repository (or the harness lab) must adopt the platform upgrade before
syncing protocol-2 governance, and its `harness-sync-preview` blocks until it does.

## Safety behavior

- No external source → exit `0` without failing CI; a source with no skill folders
  → exit `0`; a malformed folder → skipped and reported.
- `skills-lock.json` is always refreshed from `.github/skills-external/`.
- Generated Antigravity skills are skipped on re-sync by comparing against
  `.agents/skills/.generated-manifest.tsv`.
- Catalog references to absent skills are warnings, not errors, so
  `make purge-external-skills` still resets cleanly.

## Purge external skills (reset template)

`make purge-external-skills` removes `.github/skills-external/`, the legacy
installer folders and `skills-lock.json`, recreates the empty external folder and
rebuilds every native view, adapter region and the catalog with internal skills
only.
