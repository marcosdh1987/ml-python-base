# Harness release lifecycle (traceable release contract)

This template is the single authoritative source for shared governance (skills,
agents, governance docs, adapter templates). Downstream consumers — including the
`ai-agentic-harness-lab` — adopt it only as an **immutable SemVer tag**, never from
mutable `main`. The traceable release contract makes each release coherent and
machine-verifiable while keeping every repository-boundary operation manual.

## Principles

- **Read-only tooling.** `scripts/harness_release.py` validates, classifies, and
  prepares. It never commits, tags, pushes, merges, or publishes.
- **Manual publication.** A human runs the printed `git tag` / `gh release` commands.
- **Governance vs. platform are separate channels.** Governance paths are safe to
  project from a release; platform paths (sync engine, `Makefile`, `registry.toml`,
  packaging) require a separate reviewed PR and a MAJOR-style review.
- **Provenance is recorded.** Governance releases carry the originating proposal,
  issue, and PR.

## SemVer policy

Apply strictly even on `0.x`:

- **PATCH** — compatible correction or clarification, no new capability.
- **MINOR** — additive compatible rule, skill, agent, template, or supported tool.
- **MAJOR** — removal, rename, contract break, incompatible registry/layout change,
  or sync-protocol migration.

The governance/platform allowlist and the sync `protocol` live in
`adapters/registry.toml` under `[template_sync]`.

## Commands

| Target | Purpose |
|---|---|
| `make harness-change-summary BASE_REF=v0.1.0` | Classify changes; recommend a bump. |
| `make harness-platform-summary BASE_REF=v0.1.0` | Report platform changes + migration need. |
| `make harness-release-check VERSION=0.2.0 [BASE_REF=…] [PROPOSAL=…] [ISSUE=…] [PR=…] [REQUIRE_PROVENANCE=1] [ALLOW_PLATFORM=1] [SKIP_GATES=1]` | Read-only preflight. |
| `make harness-release VERSION=0.2.0` | Preflight + print the manual tag/publish steps. |
| `make harness-release-manifest VERSION=0.2.0 PUBLISHED_AT=<iso8601>` | Generate the release asset **after** the tag exists. |

The preflight verifies: valid SemVer; `pyproject.toml` and `CHANGELOG.md` agree with
the requested version; the tag does not already exist; a clean working tree;
governance/platform classification against `BASE_REF`; and, when required, proposal/
issue/PR provenance. It also runs `make check` and `make check-sync` unless
`SKIP_GATES=1`.

## Publishing a release (manual)

1. Reconcile `pyproject.toml` and `CHANGELOG.md` to the target version.
2. `make harness-release-check VERSION=X.Y.Z BASE_REF=<prev-tag>` — must pass.
3. `make harness-release VERSION=X.Y.Z` — copy the printed commands.
4. Run them manually: create and push the annotated `vX.Y.Z` tag, then
   `gh release create`.
5. `make harness-release-manifest VERSION=X.Y.Z PUBLISHED_AT=<iso8601>` and attach
   the generated `harness-release-vX.Y.Z.yaml` to the GitHub Release.

The release manifest schema is `schemas/harness-release-v1.schema.json` (see
`docs/../schemas`). The deprecated `make template-release` target — which used to
auto-commit and auto-tag — now refuses to run and points here.

## Proposing a change

Open a **Harness improvement proposal** issue (`.github/ISSUE_TEMPLATE/harness-improvement.yml`).
It is sanitized (no secrets, logs, local paths, or raw run data) and links to a
reviewed HEP proposal in the lab. Expected labels: `lab-proposal`,
`harness-governance` / `harness-platform`, `semver:patch|minor|major`,
`validation-required`.
