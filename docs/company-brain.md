# Company brain — the organizational context layer

This template is the **execution layer** of a two-layer context model: it governs
*how work is done* (rules, skills, gates, working loop). The complementary layer —
*what the organization knows* — lives in a separate repository instantiated from
[`company-brain-template`](https://github.com/marcosdh1987/company-brain-template):
domain, decisions, glossary, conventions, systems map, and runbooks, all
agent-readable Markdown owned by the organization itself.

```text
this template (semver releases, template-sync)   → shared engineering harness
        +
company brain (one instance per organization)    → organizational context
        =
effective context of every repository (CLAUDE.md / AGENTS.md import both)
```

## When to reach for it

**Not on day one of a single-repo project.** For one repository, the project
brain lives *inside* the repo in the containers this template already ships:
`memory/`, `docs/adr/`, `.github/domain-boundaries.md`. The separate brain
repository earns its existence only when a **second repo starts duplicating the
first one's context** — then the shared parts are moved (not copied) there.

## Why two repositories

- The harness is **reusable across organizations** and updated by releases; mixing
  client context into it would fork it per client and kill reuse.
- The brain is **owned by the organization** it describes — plain Markdown in their
  git, no lock-in — and is stack-agnostic (works the same for Python, TS or mobile
  repos).

## What lives where

| Concern | Here (harness) | Company brain |
|---|---|---|
| Engineering rules, gates, working loop | ✔ | |
| Skills (procedures) | ✔ — distributed by releases | referenced |
| Domain, glossary, business rules | | ✔ |
| Org-level ADRs, conventions, runbooks | | ✔ |
| Single-repo ADRs, project memory | each project repo | |

## The bootstrap skill

`bootstrap_company_brain` (in `.github/skills/`) instantiates and populates a brain
for a new organization: it mines real sources first (repos, docs, configs),
interviews humans only for the gaps, and never invents domain facts. Run it from
any supported tool against a fresh clone of `company-brain-template`.

The brain's maintenance skills (`update_domain_context`, `record_decision`,
`add_runbook`, `quarterly_context_review`) ship inside the brain template itself;
they follow this template's skill format and may be promoted here in a future
release.

## Adoption in project repos

Each project repo imports both layers from its adapters. The ready-to-paste block
lives in the brain template at `examples/repo-claude-md-snippet.md`; the adoption
guide is `docs/adoption.md` there. After adding the skill here, refresh native
layouts with `make sync-skills`.
