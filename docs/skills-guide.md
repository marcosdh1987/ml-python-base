# Skills guide

How the skills system of this harness works, in the order a new developer needs
it. Ten minutes, with examples. The machine-generated inventory lives in
[`docs/generated/skills-catalog.md`](generated/skills-catalog.md); this page
explains the ideas behind it. Engine internals are in
[`docs/skills-management.md`](skills-management.md).

## 1. What a skill is

A skill is a governed, reusable **procedure written in Markdown** that an AI coding
agent reads on demand: when to use it, what input it needs, the steps, the output
shape. It is not code the harness executes and not a prompt pasted into every
session. It is loaded only when the task matches, which keeps context small.

Every skill is a `SKILL.md` (or a flat `<name>.md`) with YAML frontmatter:

```yaml
---
name: systematic_debugging
description: Use when diagnosing a bug, failing test, or unexpected behavior — …
summary: Reproduce → isolate → hypothesize → fix → verify a bug, one cause at a time
family: quality-testing-debugging
visibility: developer
profile: core
small_model_path: true
triggers: [failing test, traceback, keyerror, bug]
---
```

`description` is the trigger the model reads. The other keys are catalog
metadata (section 4).

**Skill vs agent vs command.** A *skill* is a procedure. An *agent*
(`.github/agents/`) is a role: a tier (`planner` / `executor` / `fast`), allowed
tools and the skills it is bound to. A *slash command* (`.claude/commands/`) is a
Claude-Code-only shortcut. Skills are the portable layer: the same file serves
Claude Code, Codex, OpenCode, Antigravity and Copilot.

## 2. Two sources, five projections

| Where | What | Who edits it |
|---|---|---|
| `.github/skills/` | internal skills (source of truth) | you |
| `.github/skills-external/` | vendored third-party skills | nobody — `make sync-skills` re-imports them |
| `.claude/skills/`, `.codex/skills/`, `.opencode/skills/`, `.agents/skills/` | generated native views | the engine |
| the block between `BEGIN/END GENERATED SKILLS` in `CLAUDE.md`, `AGENTS.md`, `OPENCODE.md`, `.agents/rules/GEMINI.md`, `.github/copilot-instructions.md` | what each model sees first | the engine |

`make sync-skills` regenerates every projection; `make check-sync` fails CI if
any is stale. Never hand-edit a generated path — it is overwritten on the next
sync and the drift gate catches it anyway.

## 3. The catalog: entrypoints, primitives, optional

A developer should not have to know 25 names. The catalog is layered by
**visibility**:

| Visibility | Meaning | Listed in adapters? | Projected natively? |
|---|---|---|---|
| `developer` | an entrypoint you think in ("implement a feature") | first, with an intent line | yes |
| `internal` | a primitive the entrypoints compose | compact list | yes |
| `optional` | a specialist behind a profile | after the core list | yes |
| `hidden` | usable when named, never listed | no | yes |
| `legacy` | a retired name; maps to a replacement | only as `old → new` | **no** |

The nine entrypoints, by intent:

| I want to… | Use |
|---|---|
| start a project from this template | `bootstrap_project` |
| explore a scoped idea or compare options | `brainstorm_quick` |
| design a new subsystem or a design-impacting change | `brainstorming` |
| implement a feature or an approved plan | `plan_and_execute_feature` |
| fix a failing test, traceback or wrong behavior | `systematic_debugging` |
| plan a code, data or architecture migration | `generate_migration_plan` |
| check current facts (versions, APIs, releases) | `research_current_info` |
| verify the work before calling it done | `verify_changes` |
| review the finished diff | `requesting-code-review` |

Everything else (`create_domain_contract`, `test-driven-development`,
`generate_e2e_tests`, `retrospective`, `writing-plans`, …) still exists and is
still invocable. It is composed by the entrypoints, so you only reach for it when
the task *is* exactly that step.

## 4. Families and profiles

**Family** says what a skill is about. There are ten: `lifecycle`, `ideation`,
`planning-execution`, `architecture-contracts`, `quality-testing-debugging`,
`documentation-memory`, `git-delivery`, `research`, `specialist`, `legacy`.

**Profile** says which kind of project needs it: `core` (every project),
`python-ml` (`create_mle_agent_package`), `frontend` (`ui-ux-pro-max`),
`company-context` (`bootstrap_company_brain`), `legacy`. A profile is one value
per skill; the catalog groups skills by it so a template consumer can see what to
drop.

Both vocabularies are declared once in `adapters/registry.toml` under
`[catalog]` and validated on every sync: a typo in a family name fails
`make sync-skills`.

## 5. How the model picks a skill

Three signals, in the order the model meets them:

1. **The adapter block** (about 5 KB). Intent lines first, then primitives, then
   optional skills, then the routing rules, the small-model path, the policies and
   the legacy names. This is all a small model has to read to route correctly.
2. **The `description`** in the native `SKILL.md`. Tools that support skill
   discovery (Claude Code, OpenCode, Codex) match the request against it.
3. **The routing rules**, stated in prose in every adapter:
   - bounded change → `brainstorm_quick` or straight to `plan_and_execute_feature`;
     new subsystem / design impact / ambiguous architecture → `brainstorming`;
   - approved plan → `plan_and_execute_feature` with `mode: execute_only`;
   - failing test → `systematic_debugging` before any edit;
   - before "done" → `verify_changes`; review of the diff → `requesting-code-review`.

You can ask the catalog what it would do without a model:

```bash
make route PROMPT="pytest fails with KeyError in repository.py"
# → {"skill": "systematic_debugging", "family": "quality-testing-debugging", "mode": "full", …}
```

That deterministic router reads each skill's `triggers`; it is the executable form
of the routing rules and the basis of the routing tests (section 11).

## 6. Invoking a skill explicitly

| Tool | How |
|---|---|
| Claude Code | `/verify_changes`, or "use the `verify_changes` skill" |
| Codex | `@verify_changes` in the composer (reads `.codex/skills/`) |
| OpenCode | ask for it by name; the `skill` tool loads `.opencode/skills/<name>/SKILL.md` |
| Antigravity | name it; it reads `.agents/skills/<name>/SKILL.md` |
| Copilot | name it; the instructions file tells it to read `.github/skills/<name>.md` |

A retired name still works: asking for `source-command-verify` routes to
`verify_changes` because the adapter block says so. It is not projected anywhere,
so it never competes with the real skill.

## 7. How skills compose

"Implement the payment-retry feature" runs the feature entrypoint, which composes
the primitives without you naming them:

```
plan_and_execute_feature
  ├─ (design unclear?) brainstorm_quick   ← or brainstorming for a new subsystem
  ├─ create_domain_contract               ← new use case / repository boundary
  ├─ test-driven-development              ← failing test first
  ├─ implementation                        ← the code
  ├─ generate_e2e_tests                   ← when a critical flow changed
  ├─ generate_implementation_docs         ← docs/ page (CI enforces it)
  ├─ verify_changes                       ← make check, make check-sync
  └─ retrospective                        ← durable learnings into memory/
```

`mode: execute_only` enters at the implementation step when a plan is already
approved. `mode: local_model_32k` turns the same flow into a one-step-per-turn
backlog for small models (section 10).

## 8. External (vendored) skills and policies

Twelve skills come from third parties (mostly `obra/superpowers`). They are
copied under `.github/skills-external/` with their upstream and licence recorded
in `adapters/registry.toml` (`[external_skill.*]`) and `skills-lock.json`; a
missing licence fails `make check`.

Two problems come with vendoring: a trigger that conflicts with governed routing
(`brainstorming` shipped "you MUST use this before ANY creative work"), and steps
this repository forbids (`finishing-a-development-branch` runs `git merge` and
`git push`). Editing the vendor file is not an option — the next sync overwrites
it and a silent fork loses upstream fixes.

The answer is a **projection-time overlay**, declared in the registry:

```toml
[skill.brainstorming]
visibility = "developer"
description = "Use for design-impacting work: a new subsystem, … For a bounded change use `brainstorm_quick`."

[policy.git-actions]
title = "Git actions are recommendations"
summary = "Agents may recommend git actions and prepare commands … They MUST NOT run `git commit`, `git push`, merge, rebase, or delete branches unless the user explicitly asks …"
applies_to = ["brainstorming", "finishing-a-development-branch", "writing-plans", …]
```

For an overlaid skill the *projected* `SKILL.md` is generated: governed
frontmatter, a short banner naming the policies that take precedence, then the
vendor body verbatim. The source file, its hash in the lock and its licence stay
untouched. A test fails if any vendored skill instructs a mutating git action
without being covered by the policy, and Claude Code's `settings.json` asks before
any `git commit` / `git push` / `git merge` regardless.

### Where the policy is actually enforced

Prose reaches the model; it does not stop a tool call. Where a platform exposes
a permission primitive, the same rule is projected into it, derived from one
list (`skills_sync.permissions`) so the dialects cannot drift.

| Tool | Instruction level | Tool / permission level | How |
|---|---|---|---|
| Claude Code | yes | **yes** | `permissions.ask` in `.claude/settings.json` — the command runs only after you approve it |
| OpenCode | yes | **yes** | `permission.bash` glob map in `opencode.json`, and the same map projected into every generated `.opencode/agents/*.md` that may run shell |
| GitHub Copilot (VS Code) | yes | **opt-in** | `chat.tools.terminal.autoApprove` rules shipped as `.vscode/settings.recommended.json`; workspace settings are gitignored, so you copy it to `.vscode/settings.json` to adopt it |
| Codex | yes | **no primitive** | Codex's approval control is a session/global setting (`approval_policy`, `sandbox_mode`), not a per-command repository rule; nothing command-scoped to project |
| Antigravity / Gemini | yes | **no primitive** | Workspace rules are instructions only; approvals are decided in the product UI |

`ask`, never `deny`: the policy lets you authorize a specific action in the
session, and `deny` would refuse even when you asked for it. For the two tools
with no primitive, the instruction-level statement in their adapter file plus
the banner in each projected `SKILL.md` is the whole of the protection — treat a
run there as un-gated and review the diff before it leaves your machine.

## 9. Progressive disclosure

Context is the bottleneck, so each layer is as small as it can be:

- the adapter block lists one line per skill (`summary`, at most 140 characters);
- the model opens the `SKILL.md` only for the skill it selected;
- references and scripts inside a bundle (`brainstorming/visual-companion.md`,
  `subagent-driven-development/implementer-prompt.md`) are read only when a step
  points at them;
- `hidden` and `legacy` skills are not listed at all.

## 10. Small and self-hosted models

The catalog does not assume a frontier model. The adapter block carries a
**small-model line** pointing at `LOCAL_AGENT.md` (edit never rewrite, one root
cause per turn, one or few files per step, declare target / change / validation,
run it, stop) and names the skills that carry an explicit small-context mode
(`small_model_path: true`): `plan_and_execute_feature` (`mode: local_model_32k`),
`systematic_debugging`, `brainstorm_quick`, `verify_changes`. The Copilot adapter
puts that mode above everything else, and the mechanical caps (gateway
`max_tokens`, served context) are documented in
[`docs/local-model-runtime-config.md`](local-model-runtime-config.md) and
[`docs/task-sizing.md`](task-sizing.md).

## 11. Adding a skill

1. Write `.github/skills/<name>.md` (or `<name>/SKILL.md` with helpers). Give it
   the frontmatter of section 1: a `description` written as a trigger, a
   `summary` under 140 characters, `family`, `visibility` (`internal` unless it is
   a genuine entrypoint), `profile`, `risk`, and 4–10 `triggers`.
2. If it composes other skills, say so in its body; if an entrypoint should call
   it, mention it there.
3. Add one scenario to `tests/routing/scenarios.toml` that should route to it and
   one overlap scenario that should not.
4. `make sync-skills`, then `make check` (runs the catalog validation and the
   routing evals) and `make check-sync`.
5. Optionally measure it with the harness lab (section 13).

For a vendored skill: install it, `make sync-skills`, add `[external_skill.<name>]`
with upstream and licence, add a `[skill.<name>]` overlay for its metadata, and
add it to a policy's `applies_to` if its body instructs anything the repository
forbids.

## 12. Deprecating a skill

Two shapes, both keep old prompts working:

- **Keep the file, hide it:** set `visibility: legacy` and `replacement: <live skill>`
  in its frontmatter (or overlay). It stops being projected; adapters map
  `old → new`.
- **Delete the file, keep the name:** remove it and add
  `[alias.<old>] replacement = "<live skill>"` to the registry. This is what
  happened to `source-command-verify`, `source-command-retro`,
  `execute_engineering_task`, `create_use_case` and `create_repository_interface`.

Validation refuses a legacy skill or alias whose replacement is not live, and the
routing tests assert every legacy name resolves.

## 13. Validating a skill

| Question | Command |
|---|---|
| Is the catalog consistent and every projection current? | `make check-sync` |
| Does the catalog route the scenarios as intended? | `make routing-eval` (part of `make check`) |
| What would a real model pick, given only the adapter block? | `make routing-eval-live [RUNNER=claude\|opencode] [MODEL=…] [ADAPTER=…]` |
| Does the skill change outcomes on real tasks? | the harness lab: ablate it (Lane A) or trial a staged copy (Lane B), N repetitions per arm |

The live eval prints one line per scenario and a pass count; point `ADAPTER` at
a saved copy of an older adapter file to compare two catalog versions.

## Cheat sheet

```bash
make sync-skills        # regenerate every projection + docs/generated/skills-catalog.md
make check-sync         # drift gate (CI)
make route PROMPT="…"   # what the catalog routes a request to
make routing-eval       # deterministic routing scenarios
make routing-eval-live  # same scenarios against a real model (opt-in)
```
