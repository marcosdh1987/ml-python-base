# Skills catalog v3 — audit, target state and validation evidence

Working record of the catalog reorganisation (2026-09-12). The durable decision is
ADR-0002; the developer guide is `docs/skills-guide.md`; the engine reference is
`docs/skills-management.md`. This page keeps the evidence: what was found, what
changed, and how it was validated against the template's own gates and against the
xmartlabs harness lab.

## 1. Current-state audit (before)

Inventory taken from the governed sources, not from documentation: 15 internal
skills (`.github/skills/`), 12 external (`.github/skills-external/`), 27 projected
identically into `.claude/`, `.codex/`, `.opencode/`, `.agents/`, and listed flat in
all five adapter files. Baseline gates green (`make check-sync`, 134 tests).

| Finding | Evidence |
|---|---|
| duplicate capability | `source-command-verify` ≡ `verify_changes`; `source-command-retro` ≡ `retrospective`. Both first-party, parked under `skills-external/` for a historical engine limitation. No consumer by name in the lab or in `ml-langchain-agent` (only generated artifacts mention them). |
| legacy alias | `execute_engineering_task`, `create_use_case`, `create_repository_interface` no longer exist here but were listed twice in `README.md` and still live in `ml-langchain-agent`. |
| overlapping trigger | vendored `brainstorming`: "You MUST use this before ANY creative work" + `<HARD-GATE>` neutralised `brainstorm_quick`; `.agents/rules/GEMINI.md` told the model to "choose the stricter one", contradicting `docs/skills-management.md`. |
| conflicting instruction / unsafe side effect | `finishing-a-development-branch` runs `git merge`, `git push`, `gh pr create`, `git branch -D`; `writing-plans`, `subagent-driven-development`, `brainstorming`, `using-git-worktrees`, `executing-plans` instruct commits. The "NEVER commit/push" rule existed only in `AGENTS.md` and `GEMINI.md`. |
| documentation drift | three hand-maintained skill lists (`README.md`, `.github/skills/README.md`, `docs/skills-management.md`) disagreed with each other and with the tree. |
| cloud-only assumption | `requesting-code-review`, `subagent-driven-development`, `executing-plans` assume subagents / a Task tool; no degradation note. |
| weak-model capability | `local_model_32k`, `LOCAL_AGENT.md`, `docs/task-sizing.md`, Copilot adapter: sound, but nothing in the catalog metadata routed to it. |
| context cost | generated adapter block: 6.4 KB of flat descriptions per adapter (the `ui-ux-pro-max` line alone ~900 chars). |
| engine | `Skill` = name/kind/description; no family, visibility or profile. Adapter templates are a governance path while the engine is platform. |

## 2. Target state (after)

- **Metadata per skill** (frontmatter for internal, `[skill.<name>]` overlay for
  vendored): `family`, `visibility`, `profile`, `auto_trigger`, `maturity`, `risk`,
  `small_model_path`, `triggers`, `replacement`, `summary`.
- **Visibility drives projection**: 9 `developer` entrypoints, 12 `internal`
  primitives, 3 `optional` specialists, 1 `hidden`, 5 legacy names (not projected).
- **Projection-time overlays** for vendored skills with a policy or description
  override; **`git-actions` policy** rendered everywhere and tested.
- **Generated catalog** + **wiki guide**; no hand-maintained lists.
- **Routing evals** (30 scenarios) in CI; live eval opt-in.
- **Protocol 2** for template sync.

## 3. Final taxonomy

| Skill | Before | After | Family | Visibility | Profile | Replacement / notes |
|---|---|---|---|---|---|---|
| `bootstrap_project` | flat | entrypoint | lifecycle | developer | core | |
| `brainstorm_quick` | flat, shadowed by vendor trigger | entrypoint | ideation | developer | core | small-model path |
| `brainstorming` (ext) | flat, "MUST use before ANY creative work" | entrypoint, governed description, git policy | ideation | developer | core | overlay |
| `plan_and_execute_feature` | flat | entrypoint | planning-execution | developer | core | `execute_only`, `local_model_32k` |
| `systematic_debugging` | flat | entrypoint | quality-testing-debugging | developer | core | small-model path |
| `generate_migration_plan` | flat | entrypoint | planning-execution | developer | core | |
| `research_current_info` | flat | entrypoint | research | developer | core | risk `network` |
| `verify_changes` | flat | entrypoint | quality-testing-debugging | developer | core | small-model path |
| `requesting-code-review` (ext) | flat | entrypoint | quality-testing-debugging | developer | core | |
| `create_domain_contract` | flat | primitive | architecture-contracts | internal | core | |
| `refactor_to_clean_architecture` | flat | primitive | architecture-contracts | internal | core | |
| `validate_module_structure` | flat | primitive | architecture-contracts | internal | core | |
| `generate_e2e_tests` | flat | primitive | quality-testing-debugging | internal | core | |
| `test-driven-development` (ext) | flat | primitive | quality-testing-debugging | internal | core | |
| `generate_implementation_docs` | flat | primitive | documentation-memory | internal | core | |
| `retrospective` | flat | primitive | documentation-memory | internal | core | |
| `writing-plans` (ext) | flat | primitive, git policy | planning-execution | internal | core | overlay |
| `executing-plans` (ext) | flat | primitive, git policy | planning-execution | internal | core | overlay |
| `subagent-driven-development` (ext) | flat | primitive, git policy | planning-execution | internal | core | overlay |
| `using-git-worktrees` (ext) | flat | primitive, git policy | git-delivery | internal | core | overlay, risk `git-mutating` |
| `finishing-a-development-branch` (ext) | flat | primitive, git policy | git-delivery | internal | core | overlay, risk `git-mutating` |
| `create_mle_agent_package` | flat | optional | architecture-contracts | optional | python-ml | |
| `ui-ux-pro-max` (ext) | flat, 900-char description | optional, short summary | specialist | optional | frontend | |
| `writing-clearly-and-concisely` (ext) | flat | optional | documentation-memory | optional | core | |
| `bootstrap_company_brain` | flat | hidden | lifecycle | hidden | company-context | usable when named |
| `source-command-verify` | flat (duplicate) | **removed**, alias | legacy | legacy | legacy | → `verify_changes` |
| `source-command-retro` | flat (duplicate) | **removed**, alias | legacy | legacy | legacy | → `retrospective` |
| `execute_engineering_task` | absent, listed in README | alias | legacy | legacy | legacy | → `plan_and_execute_feature` (`execute_only`) |
| `create_use_case` | absent, listed in README | alias | legacy | legacy | legacy | → `create_domain_contract` |
| `create_repository_interface` | absent, listed in README | alias | legacy | legacy | legacy | → `create_domain_contract` |

## 3b. The nine developer entrypoints, justified


Checked mechanically: none is `legacy`, none carries a `replacement`, all are
`maturity: stable`, and each has exactly one intent row
(`tests/routing/test_routing.py::test_intents_point_at_developer_entrypoints`).
So none survived as a backward-compatibility shim.

| Entrypoint | Developer intent | Why it must be visible | Why it cannot be an internal primitive |
|---|---|---|---|
| `bootstrap_project` | "start a project from this template" | It is the first thing a developer does with a fresh clone; nothing else can compose it | It has no caller — it *is* the entry to the repository's lifecycle |
| `brainstorm_quick` | "explore a scoped idea or compare options" | The cheap half of the ideation fork; invisible, every idea would fall into the heavy design gate | It is a decision point a human makes, not a step another skill runs |
| `brainstorming` | "design a new subsystem or a design-impacting change" | The expensive half of that same fork, with a user-approval gate that only a human can pass | Its terminal state is a spec the user approves — an entrypoint by construction |
| `plan_and_execute_feature` | "implement a feature or an approved plan" | The single orchestrator for delivery; it is what composes the primitives | It is the composer, not the composed |
| `systematic_debugging` | "fix a failing test, traceback or wrong behavior" | The most frequent non-feature request, and the one where an un-routed agent thrashes worst | A bug report arrives from the user, so the routing must exist at the top level |
| `generate_migration_plan` | "plan a code, data or architecture migration" | Migrations are a distinct risk class needing rollback and checkpoints before code | Nothing else invokes it; a migration is requested, not derived from a feature |
| `research_current_info` | "check current facts (versions, APIs, releases)" | The only skill that leaves the repository (`risk: network`); the user must be able to ask for it deliberately | It answers a question rather than advancing an implementation, so no orchestrator owns it |
| `verify_changes` | "verify the work before calling it done" | The closing gate of the working loop, and the one an agent is most tempted to skip | `plan_and_execute_feature` does call it — but a user also asks for it alone, mid-work, on someone else's diff |
| `requesting-code-review` | "review the finished diff" | A distinct act from verification: a second opinion on finished work, before merge | The request comes from a human deciding the work is ready |

The two that are also composed (`verify_changes`, and ideation before planning)
stay visible because a developer asks for them directly and out of sequence. The
rest have no caller at all.

## 4. Before / after

| Measure | Before | After |
|---|---|---|
| names a developer must know | 27 (flat) | 9 entrypoints (+ intents table) |
| skills available to the model | 27 | 25 discoverable/hidden (the 2 removed were duplicates; 5 legacy names still resolve) |
| generated block, `CLAUDE.md` | 6 381 B | 5 185 B (−19%), now including routing rules, policy, small-model line, aliases |
| generated block, `.github/copilot-instructions.md` | 6 406 B | 5 139 B (−20%) |
| contradictory ideation triggers | 2 (`brainstorming` description, GEMINI prose) | 0 |
| adapters carrying the git rule | 2 of 5 | 5 of 5 (+ policy rendered in all, + Claude `ask` rules) |
| hand-maintained skill lists | 3 | 0 (generated catalog) |
| routing tests | 0 | 30 scenarios + 8 structural invariants, in `make check` |
| template tests | 134 | 203 |

## 4b. The five legacy aliases

Every column below is a test in `tests/skills_sync/test_aliases.py` (37 cases),
so the table cannot drift from the behaviour.

| Legacy name | Canonical destination | Projected? | Available for migration? | Can auto-trigger? | Why it still exists |
|---|---|---|---|---|---|
| `source-command-verify` | `verify_changes` | no | yes | no | First-party mirror of the `/verify` command; old prompts and saved benchmark cases may still say it |
| `source-command-retro` | `retrospective` | no | yes | no | First-party mirror of the `/retro` command; same reason |
| `execute_engineering_task` | `plan_and_execute_feature` (`mode: execute_only`) | no | yes | no | Removed before v3 but still shipped by `ml-langchain-agent`, which has not synced |
| `create_use_case` | `create_domain_contract` (`contract_type: use_case`) | no | yes | no | Same: still live downstream |
| `create_repository_interface` | `create_domain_contract` (`contract_type: repository`) | no | yes | no | Same: still live downstream |

What each column is proved by:

- **Projected? no** — no directory under `.claude/skills/`, `.codex/skills/`,
  `.opencode/skills/` or `.agents/skills/`, and no governed source file.
- **Available for migration? yes** — routing a prompt that names the old name
  returns the replacement, with `resolved_from` recording the old name.
- **Can auto-trigger? no** — an alias is metadata, not a skill: it has no
  description a model could match and appears in adapters only inside the
  one-line `old → new` mapping, never in a list of usable skills.
- **Why it still exists** — each alias carries a mandatory `note`; an alias
  without a recorded reason fails the suite, so none can quietly become permanent.

Retirement criterion: drop an alias once no consumer says the old name. For the
three pre-v3 names that is `ml-langchain-agent`'s next template sync; for the two
first-party ones, one release cycle with no reported use.

## 5. Quality gates (ml-python-base)

| Gate | Result |
|---|---|
| `make sync-skills` | clean, idempotent |
| `make check-sync` | ✅ no drift (adapters, native views incl. overlays and legacy removals, manifest, lock, agents, catalog) |
| `make check` | ✅ ruff format/lint, bandit, mypy, 202 tests, 90% coverage |
| `make check-docs-coverage` | ✅ |
| `make routing-eval` | ✅ 30/30, 0 forbidden hits, 0 ambiguous |

## 6. Harness-lab validation — protocol v2 adoption (state A)

Run against a disposable clone of `xmartlabs/sdlc-ml-python-harness-lab` @ `42cbb29`
on a branch `harness-candidate/skills-catalog-v3`; the real checkout was not
modified.

### 6.1 What the first pass found

Copying the template's engine over the lab's broke 12 of its tests. None was a
governance regression: the lab had **extended** the engine it vendors, and the
template had no equivalent, so a platform upgrade could only be done by forking.
Classification of the 12:

| Failing tests | Cause | Verdict | Resolution |
|---|---|---|---|
| `test_projection_masked_adapters.py` (6), `test_harness_conditions.py` (5) | `link_tool(..., strategy=)` and `render_tool(..., template_root=)` absent upstream | **API that should have backward compatibility** — both are generic "project into a foreign root" extension points with a real consumer | upstreamed into `ml-python-base` (`linker.link_tool`, `renderer.render_region/render_tool`) with tests |
| `test_skill_invocation.py::test_a_native_arm_gets_its_staged_skills_placed_in_the_workspace` (1) | `linker.add_skills` absent upstream | same | upstreamed (`linker.add_skills`), now applies overlays and the legacy filter too |
| `test_cli_integration.py` (collection error) | `cli.check_drift` absent upstream | same | upstreamed (`cli.check_drift`), `_do_check` now calls it |

A second pass then surfaced two more, both genuinely the lab's to migrate:

| Failing tests | Cause | Verdict | Resolution |
|---|---|---|---|
| `test_skill_ablation.py` (6) | the lab's ablation path discovered skills **without** the registry, so a regenerated view lost overlays and left the tree dirty | **lab extension that must migrate** | 4-line patch to `scripts/bench_run.py` (pass `registry=`) |
| `test_agents.py::test_render_opencode_permission_allows_implementer_to_edit` (1) | the OpenCode agent frontmatter now nests a `bash` permission map instead of `bash: allow` | **intentional breaking change of protocol v2** | 5-line patch to the lab's copy of the test |

No failure was a regression of the new engine. The shared contract
(`discover_skills(root)`, `link_tool(root, tool, skills)`,
`render_tool(root, registry, tool, skills=)`) is unchanged and still passes the
lab's own tests for it.

### 6.2 The migration, and its result

Five steps, in order:

1. **Governance sync** — `.github/skills`, `.github/skills-external`,
   `.github/agents`, the seven governance docs, `adapters/templates`. Deletes the
   two retired first-party skill directories.
2. **Platform upgrade** — copy the template's `skills_sync/*.py`, keep the
   lab-only `projection.py`. With the four extension points upstreamed this is a
   plain copy; before it, it was an unmergeable 3-way patch.
3. **Registry** — `protocol = 2`, append the `[catalog]` / `[[intent]]` /
   `[skill.*]` / `[alias.*]` / `[policy.*]` blocks, drop the two retired
   `[external_skill.source-command-*]` entries. The lab keeps its own `[[tool]]`
   entries and the rest of its provenance table.
4. **`scripts/bench_run.py`** — pass `registry=` in `build_effective_skills` and
   `restore_full_skill_views`.
5. **`tests/skills_sync/test_agents.py`** — adopt the nested OpenCode permission
   format.

Steps 4 and 5 are the only lab-owned code changes; the patch is 14 lines total.

| Check | Result |
|---|---|
| `skills_sync sync` + `check` in the lab | ✅ clean, no drift |
| **Full lab test suite** | ✅ **1917 passed, 0 failed** (was 255 passed / 12 failed) |
| lab adapter block | 6 193 → 5 185 B, no legacy directories in native views |
| ablation round-trip (`build_effective_skills` → `apply_skill_views` → `restore_full_skill_views`) | 10 files change while ablated, **0 after restore**; the `brainstorming` overlay survives intact |

This is **state A**: the lab runs on protocol v2 with its whole suite green.

## 7. Scenario coverage (Phase 12 minimum)

| Scenario class | Deterministic routing | Live routing (Haiku) |
|---|---|---|
| feature implementation | `approved-plan-execute-only`, `bounded-timeout-change` → `plan_and_execute_feature` | §8 |
| bug / debugging | `bug-keyerror`, `small-model-bugfix` → `systematic_debugging` | §8 |
| architecture change | `design-multitenant-subsystem` → `brainstorming`; `refactor-boundaries` → `refactor_to_clean_architecture` | §8 |
| migration | `migration-plan` → `generate_migration_plan` | §8 |
| verification | `final-quality-checks`, `is-it-done` → `verify_changes` | §8 |
| weak-structure repo / small model | `small-model-spike`, `small-model-bugfix` → `local_model_32k` | §8 |
| skill discovery | `specialist-mle-package`, `specialist-ui`, `hidden-company-brain` | §8 |
| skill overlap | `quick-brainstorm-caching`, `code-review-before-merge`, `tdd-primitive`, `subagent-execution` | §8 |
| legacy aliases | `legacy-*` (5) | §8 |

## 8. Live routing eval (`claude -p --model haiku`)

Each run gives the model **only** the generated skills block of one adapter file
plus the user request, and asks which single skill it would read first. Haiku is
the small-cloud-model proxy; the block-only prompt is the small-context proxy.

| Run | Strict (skill + mode) | Skill-level | Forbidden hits |
|---|---|---|---|
| old block (`git show HEAD:CLAUDE.md`), 30 scenarios | 28/30 | 29/30 | 0 |
| v3 block, first version, 30 scenarios | 26/30 | 28/30 | 0 |
| **v3 block, hardened, 30 scenarios** | **29/30** | **30/30** | **0** |
| — of which the priority subset (14: ideation fork, feature, debugging, verification, migration, legacy) | 13/14 | 14/14 | 0 |

Reading:

- **Skill choice is better than before the change** (30/30 vs 29/30) on a block
  that is 18% smaller, and no scenario in any run chose a forbidden skill.
- **No legacy name leaked**: all five resolved to their replacement.
- The single strict miss, in every run including the old block, is
  `small-model-bugfix`: the model picks `systematic_debugging` correctly but
  labels the mode `full` rather than `local_model_32k`. The skill is right; the
  mode label is advisory and the small-model rules reach the agent through
  `LOCAL_AGENT.md` regardless. Tracked as a known gap rather than papered over.
- The first v3 run exposed a real weakness — a specialist listed below the
  entrypoints was overlooked (`specialist-ui` → null) and a bounded change got no
  skill. Both were fixed by stating in the section header that specialists apply
  *"even if no entrypoint fits"* and by naming concrete domains in
  `ui-ux-pro-max`'s summary. That is what the live eval is for.

Reproduce, or compare another model class:

```bash
make routing-eval-live                          # claude CLI, default model
make routing-eval-live MODEL=haiku              # small cloud model
make routing-eval-live RUNNER=opencode MODEL=gateway/…   # local / open-source
make routing-eval-live ADAPTER=/tmp/CLAUDE.old.md        # an older block, same scenarios
```

**Metric to watch**, in this order: (1) *forbidden hits* — must stay 0, it is the
only hard failure; (2) *skill-level match* — the routing decision itself;
(3) *strict pass* — adds the execution-mode label, which small models get wrong
more often and which matters less. The suite is model-agnostic: nothing in
`scenarios.toml` names a model, so large-cloud, small-cloud and local runs are
directly comparable.

**Local / open-source model: not run.** No local model is reachable in this
environment (`ollama` not installed, the LM Studio daemon does not start, no
`.env` and therefore no gateway base URL). The command above is the reproducible
entry point once one is available; the scenario file and the harness need no
change.

## 9. Instruction payload per adapter

The generated block is what every model reads before anything else, so the
reduction has to hold for all five adapters, not just Claude's. Measured between
the sentinels (excluding the marker lines).

| Adapter | Before (B) | After (B) | Delta | Lines |
|---|---|---|---|---|
| `CLAUDE.md` | 6 202 | 5 097 | −17.8% | 53 |
| `OPENCODE.md` | 6 204 | 5 099 | −17.8% | 53 |
| `AGENTS.md` (Codex) | 6 201 | 5 096 | −17.8% | 53 |
| `.agents/rules/GEMINI.md` (Antigravity) | 6 203 | 5 101 | −17.8% | 53 |
| `.github/copilot-instructions.md` | 6 227 | 5 051 | −18.9% | 53 |

The spread after the change is 50 bytes across five adapters (5 051–5 101), all
53 lines: no adapter kept a flat catalog. The only structural difference is the
first line — tools with a native view name their projected directory, Copilot
reads the governed paths directly — which is also why Copilot's block is the
smallest.

## 10. Policy enforcement by adapter

`git-actions` states the rule in prose for all five adapters. Prose reaches the
model, not the tool call, so where a platform exposes a permission primitive the
same rule is projected into it. Every dialect is derived from one list
(`skills_sync.permissions.GIT_MUTATING_COMMANDS`: `git commit`, `git push`,
`git merge`, `git rebase`, `git branch -d`, `git branch -D`, `gh pr merge`), and
`tests/skills_sync/test_policies.py` asserts the derivation against what is
committed.

| Adapter | Instruction level | Tool / permission level | Mechanism | Test |
|---|---|---|---|---|
| Claude Code | yes | **yes** | `permissions.ask` in `.claude/settings.json` | `test_claude_settings_ask_before_git_mutations` |
| OpenCode | yes | **yes** | `permission.bash` glob map in `opencode.json` **and** in every generated `.opencode/agents/*.md` that may run shell | `test_opencode_config_asks_before_git_mutations`, `test_projected_opencode_agents_carry_the_git_permission` |
| GitHub Copilot (VS Code) | yes | **opt-in** | `chat.tools.terminal.autoApprove` shipped as `.vscode/settings.recommended.json`; workspace settings are gitignored so the developer copies it to `.vscode/settings.json` | `test_copilot_recommended_settings_never_auto_approve_git_mutations` |
| Codex | yes | **no primitive** | approval is a session/global setting (`approval_policy`, `sandbox_mode`), not a per-command repository rule — nothing command-scoped exists to project | — |
| Antigravity / Gemini | yes | **no primitive** | workspace rules are instructions only; approvals happen in the product UI | — |

Decisions, not guesses:

- **`ask`, never `deny`.** The policy permits an explicitly requested action, and
  `deny` would refuse even then.
- **OpenCode semantics verified against its documentation**: patterns are
  wildcards (`*` = zero or more characters), and the **last** matching rule wins —
  hence `"*": "allow"` first, the seven `ask` entries after it. A test asserts
  that order.
- **Read-only agents keep `bash: deny`.** The permission map widens nothing: an
  agent that could not run shell still cannot.
- **Codex and Antigravity are reported as unprotected at tool level** rather than
  given a simulated control. A run there is un-gated; review the diff.

## 11. Remaining risks and follow-ups

- The deterministic router is a proxy for model behaviour; the live eval exists to
  catch divergence and should be run when triggers or descriptions change.
- OpenCode has no `ask`-style permission rule for git mutations yet (the policy is
  rendered in `OPENCODE.md` and in the projected skills; a `permission` rule in
  `opencode.json` needs its headless behaviour confirmed in the lab first).
- Downstream repositories (`ml-langchain-agent`, the lab) need the platform upgrade
  before syncing protocol-2 governance; the migration steps are in §6.
- `triggers` need light curation when a skill's scope changes; the routing suite
  fails loudly when they drift.
