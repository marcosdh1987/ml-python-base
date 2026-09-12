# Skills (governed source)

Operational skills receive explicit input and return structured output. This folder
is the source of truth for **internal** skills; vendored skills live in
`.github/skills-external/`. The generated inventory is
`docs/generated/skills-catalog.md`; the guide is `docs/skills-guide.md`.

## Frontmatter

Every skill starts with YAML frontmatter. `name` and `description` are required;
the rest is catalog metadata with safe defaults (see `docs/skills-management.md`
for values and semantics):

```yaml
---
name: verify_changes                      # matches the file stem or folder name
description: Use before considering work done — …   # the trigger the model reads
summary: Run the read-only gate and report pass/fail honestly   # ≤ 140 chars, adapters show this
family: quality-testing-debugging         # one of [catalog].families in adapters/registry.toml
visibility: developer                     # developer | internal | optional | hidden | legacy
profile: core                             # core | python-ml | frontend | company-context | legacy
auto_trigger: true
maturity: stable                          # stable | experimental | deprecated
risk: read-only                           # read-only | writes-files | git-mutating | network
small_model_path: true                    # documents a small-context mode
triggers:                                 # phrases for the deterministic router
  - verify
  - run the checks
---
```

Vendored skills cannot carry this block; declare theirs as `[skill.<name>]` in
`adapters/registry.toml` (the overlay wins over frontmatter field by field).

## Skill shapes

A skill is either only prose, or prose plus the files it runs. Both shapes live
here; the shape decides the layout.

| The skill is… | It goes in |
|---|---|
| A single `.md`, no helper files | `.github/skills/<name>.md` |
| Prose plus scripts, templates or references | `.github/skills/<name>/SKILL.md` with the helpers beside it |

A folder needs `SKILL.md` as its entry point; without it the folder is not a
skill and is skipped. The skill name comes from the file stem or the folder
name, not from the frontmatter.

Both shapes project correctly into every tool: symlink tools get one link per
bundled file, and the copy tool (Antigravity) preserves executable bits, so a
bundled `.sh` stays runnable in the projected view.

Point agents at the **governed** path of a bundled script
(`.github/skills/<name>/<script>`), never at a native copy. Native views are
rebuilt on every sync.

## Sources and projections

- Internal curated skills: `.github/skills/` (either shape)
- External vendored skills: `.github/skills-external/` (always folders)
- Generated native views: `.claude/skills/`, `.codex/skills/`, `.opencode/skills/`
  (symlinks; overlaid skills get a generated `SKILL.md`), `.agents/skills/` (copies)

If a skill exists in both sources, the internal one wins. `legacy` skills are not
projected at all; adapters map their name to the replacement.

Refresh every projection after a change:

```bash
make sync-skills     # then `make check-sync` to verify, `make check` to run the routing evals
```

## Governance dependency

All skills must comply with `.github/architecture.md`, `.github/standards.md` and
`.github/domain-boundaries.md`; complex tasks also with `.github/orchestration.md`.
Vendored skills whose steps contradict repository policy (for example, running
`git commit`) are projected under the `git-actions` policy declared in the registry.
