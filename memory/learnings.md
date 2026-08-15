# Learnings

> Non-obvious facts discovered while working: gotchas, why-it-is-this-way, dead ends
> to avoid. Append new entries at the top. One fact per entry.

## `make ci` is not a faithful mirror of CI: two gates only exist in the runner — 2026-08-14

The PR for issue #43 needed two extra CI round-trips despite a green local
`make check`, because two gates are invisible locally:

1. **Docs-coverage guardrail.** The `enforce-docs-and-quality` workflow rejects any
   PR that touches `src/` or `tests/` without updating at least one file under
   `docs/`. The rule lives only in the workflow YAML (and as a Runtime Rule in the
   adapter files) — no make target checks it, so `make ci` passes locally while CI
   fails.
2. **Git identity.** GitHub runners have no git config and an empty GECOS field, so
   git cannot auto-detect an identity. Tests whose *subject under test* runs real
   git commands (e.g. `harness_release.py` publish creating an annotated tag) pass
   on macOS — where git auto-detects the OS user — and die in CI with
   `fatal: empty ident name`. Env-var identity in test helpers is not enough; it
   only covers the test's own git calls, not the script's subprocesses.

**Why it matters:** a green local gate is necessary but not sufficient; both
failures were structural (environment parity), not flaky, and will recur in any
test or PR with the same shape. This also violates the repo's own
"system-enforced over model-only" principle: the docs rule is enforced nowhere a
developer or agent runs locally.
**How to apply:** (1) if a diff touches `src/` or `tests/`, include a genuine
`docs/` update before pushing; (2) fixtures for git-running code must persist
`user.name`/`user.email` in the temp repo's *local config* (see
`_configure_identity` in `tests/harness_release/test_harness_release.py`); (3) to
reproduce the CI git environment locally, run pytest under
`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CONFIG_COUNT=1
GIT_CONFIG_KEY_0=user.useConfigOnly GIT_CONFIG_VALUE_0=true` (documented in
`docs/harness-release-lifecycle.md`). Structural fix worth a follow-up: add a
`check-docs-coverage` make target mirroring the workflow rule and fold it into
`make ci`.

## Weak models need protocols front-loaded in the adapter file itself (issue #43) — 2026-08-14

Opencode runs with open-source/self-hosted models showed that pointers to skills
are not reliably followed: agents thrashed on wrong workspace roots, drifted from
the exact reported exception, skipped post-edit verification when the preferred
runner was missing, and introduced parse errors mid-edit. The fix (HEP-2026-000)
was a hybrid: canonical wording in governance (`.github/skills/systematic_debugging.md`
Execution Rules + `standards.md` Bug-Fix Discipline gates) plus a condensed,
byte-identical `## Debugging protocol` checklist inserted directly into `OPENCODE.md`
and `AGENTS.md` **before** the generated skills block, so weak models see it early.

**Why it matters:** for weak models, adapter-file placement and ordering is the
enforcement mechanism — a rule that only lives behind a skill pointer effectively
does not exist for them. Also: the issue's artifact paths (`.github/AGENTS.md`,
`.github/opencode.json`) were stale; real adapters live at the repo root, and only
the sentinel-delimited skills block is machine-owned (`make check-sync`).
**How to apply:** when a future HEP targets adapter guidance, edit the hand-written
prose outside the sentinels, keep multi-adapter copies byte-identical, leave the
skill's frontmatter `description:` untouched unless all five adapters should regen,
and always run `make sync-skills` after editing a skill body (the antigravity copy
is hash-manifested). Source: HEP-2026-000 → `marcosdh1987/ml-python-base#43`.

## Governed workflow hardened from harness audit evidence (issue #35) — 2026-07-24

The three core governance docs (`.github/architecture.md`, `standards.md`,
`domain-boundaries.md`) were tightened to close five recurring failure patterns
found across a batch of agent runs (Claude harness × Haiku/Opus, cases:
tetris-v1 + several qutebrowser/ansible/openlibrary instances). The added rules:
(1) a concrete pre-edit plan stating fix + files/symbols + verification target;
(2) a mandatory `memory/` + governance read *before* the first edit; (3) a
mandatory reproduce→isolate→hypothesize→fix→verify loop for bug fixes; (4) run
the narrowest relevant target test first, with syntax/manual only as supplements;
(5) a deterministic edge-case recipe for stateful flows (game-over/restart) plus
no lateral git/setup chores at branch finishing.

**Why it matters:** this is the baseline for the *next* improvement-cycle run. If
the changes worked, re-running the same cases through the harness should surface
fewer (ideally zero) proposals on these patterns; any that reappear mark what did
not get internalized.
**How to apply:** before re-running the cycle, diff current governance against this
entry's date. When auditing a new run, check these five behaviors first — they are
the known-weak spots. Source evidence: HEP-2026-000 →
`marcosdh1987/ml-python-base#35`.

## Claude Code gateway model names must match native alias resolution — 2026-07-07

Claude Code reads the generated `.claude/agents/*.md` `model:` frontmatter for
subagents. To make gateway-routed Claude Code behave like direct Claude Code, use
Claude Code's native aliases in agent frontmatter (`opus`, `sonnet`, `haiku`,
`fable`) and pin them with `ANTHROPIC_DEFAULT_OPUS_MODEL`,
`ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, and
`ANTHROPIC_DEFAULT_FABLE_MODEL`. The gateway must expose the exact full model IDs
Claude Code resolves to (`claude-opus-4-8`, `claude-sonnet-5`,
`claude-haiku-4-5-20251001`, `claude-fable-5`). Nonstandard local aliases such as
`claude-opus-4.8-oauth` may work as legacy LiteLLM names, but they bypass Claude
Code's native alias/capability model and can produce misleading entitlement or
model-selection behavior.

## OpenCode gateway model ids mirror LiteLLM aliases — 2026-06-23

When LiteLLM exposes a model as `model_name: nim-*`, OpenCode should list the key
under `provider.gateway.models` without the provider prefix and select it as
`gateway/<model_name>` in `.env`. The NVIDIA API key stays in the gateway config;
the repo only needs `GATEWAY_BASE_URL` and `GATEWAY_TOKEN`.

## Antigravity skill manifest tracks generated ownership — 2026-06-29

`.agents/skills/.generated-manifest.tsv` is the skills_sync ownership list, not a
complete inventory of every local `.agents/skills/*/SKILL.md` directory. Runtime or
local-only skill dirs can sit beside generated skills; manifest/hash tests should
iterate manifest entries, not every local skill directory.

## How this template is wired for agents — 2026-06-22

The single source of truth for governance and skills lives in `.github/`; native
tool layouts (`.claude/`, `.opencode/`, `.agents/`, `.codex/`) are **generated** by
the `skills_sync` engine. Never hand-edit generated skill links or the region
between the `BEGIN/END GENERATED SKILLS` sentinels in adapter files — run
`make sync-skills` instead, and `make check-sync` to verify nothing is stale.

**Why it matters:** hand-edits to generated artifacts are silently overwritten and
break the CI drift gate.
**How to apply:** edit `.github/skills/*.md` (source) and regenerate.

<!-- Add new learnings above this line -->
