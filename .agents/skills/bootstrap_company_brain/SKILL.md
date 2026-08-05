---
name: bootstrap_company_brain
description: Use when instantiating this company-brain template for a new organization — guides the interview-and-mine process that fills domain, glossary, conventions, architecture and ownership from real sources (repos, docs, team interviews), replacing every _PENDIENTE_ marker with verified content.
---

# Skill: bootstrap_company_brain

## Purpose

Turn an empty clone of `company-brain-template` into a populated, owned company
brain for one organization. The skill mines existing sources first (repos, docs,
tickets), then interviews humans only for what mining cannot answer, and never
invents domain facts.

## Required Input

- Organization name and the client/team contact who will own the brain.
- Read access to: the organization's main repos, any existing docs/wiki, and
  (optional) the AI gateway config if one exists.
- 60-90 min of interview time with 1-2 senior people (can be async written).

## Execution Rules

1. **Init.** Run `make init ORG=<name>`. It replaces the org placeholder across
   the repo, stamps dates, and prints the section checklist. Never skip this.
2. **Mine before asking.** For each section, extract candidate content from real
   sources and mark provenance:
   - `domain/*` and `glossary.md` ← READMEs, models/schemas, API contracts,
     product docs, recurring terms in issues/PRs.
   - `architecture/systems-map.md` ← repo list, docker-compose/IaC, CI configs.
   - `conventions/*` ← observed branch names, PR templates, linter configs,
     actual merge behavior (what people do, not what they say).
   - `team/ownership.md` ← CODEOWNERS, top committers per area.
3. **Interview to close gaps.** Prepare one focused question list per section —
   only for what mining could not answer or where sources contradict each other.
   Contradictions are asked explicitly ("docs say X, code does Y — which is
   true today?").
4. **Write with the section's own format.** Every file already defines its
   structure and quality bar in its header note. Respect tables, IDs (BR-NNN),
   and ADR numbering. Replace `_PENDIENTE_` only with verified content; leave
   the marker where nothing reliable exists yet — a visible gap beats a
   plausible invention.
5. **AI policy is mandatory.** `brain/ai-policy.md` must leave bootstrap with
   its "herramientas aprobadas", "datos" and "responsabilidad" sections filled
   and approved by the client contact. This is the one section that cannot stay
   `_PENDIENTE_`.
6. **Assign owners.** Every section in `team/ownership.md` gets a named human
   owner before the bootstrap is declared done. No owner, no section.
7. **Record the founding ADR.** Complete `decisions/0001-…` with real date and
   decision-makers.
8. **Gate.** `make validate` must pass. Then generate the adoption snippet for
   each target repo (see `docs/adoption.md`) and hand it to the team.

## Output Format

- Populated brain with per-section provenance (source-mined vs interviewed).
- Remaining `_PENDIENTE_` markers listed with a proposed owner and date each.
- The adoption snippets for the organization's repos, ready to paste.
- Suggested next step: `quarterly_context_review` scheduled 90 days out.
