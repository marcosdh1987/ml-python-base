# Skills Catalog

Operational skills must receive explicit input and return structured output.

Every skill must include YAML frontmatter with:

- `name`: the skill name, matching the file or folder name
- `description`: semantic trigger description for native skill discovery

## Skill shapes

A skill is either only prose, or prose plus the files it runs. Both shapes live
in `.github/skills/`; the shape decides the layout.

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

## Skill Sources

- Internal curated skills: `.github/skills/` (either shape)
- External synced skills: `.github/skills-external/` (always folders)
- Claude Code native generated links: `.claude/skills/`
- Antigravity native generated copies: `.agents/skills/`
- OpenCode native generated links: `.opencode/skills/`

Precedence rule:

- If a skill exists in both places, prefer `.github/skills/`.

Refresh all native adapter views after internal or external skill changes:

```bash
make sync-skills
```

Or refresh individually:

```bash
make setup-claude-skills
make setup-antigravity-skills
make setup-opencode-skills
```

## Available Skills

- `bootstrap_project`
- `brainstorm_quick`
- `create_domain_contract`
- `create_mle_agent_package`
- `generate_e2e_tests`
- `generate_implementation_docs`
- `refactor_to_clean_architecture`
- `validate_module_structure`
- `generate_migration_plan`
- `plan_and_execute_feature`
- `research_current_info`
- `systematic_debugging`
- `retrospective`
- `verify_changes`

## Governance Dependency

All skills must comply with:

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

For complex tasks, also comply with:

- `.github/orchestration.md`
