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

The tag is the **last** step. `pyproject.toml` and `CHANGELOG.md` define the version;
the tag only records a commit that already carries it. Creating the tag first inverts
that relationship and the preflight will reject the release — by design, since a
published tag is never moved.

1. Reconcile `pyproject.toml` and `CHANGELOG.md` to the target version.
2. `make harness-release-check VERSION=X.Y.Z BASE_REF=<prev-tag>` — must pass.
3. `make harness-release VERSION=X.Y.Z` — copy the printed commands. It prints the
   exact, numbered sequence below.
4. Run them manually:

   ```bash
   # 1. Create and push the immutable annotated tag
   git tag -a vX.Y.Z -m "Template release vX.Y.Z"
   git push origin vX.Y.Z
   # 2. Create the GitHub Release
   gh release create vX.Y.Z --title vX.Y.Z --notes "Template release vX.Y.Z"
   # 3. Generate the release manifest (written to the git-ignored dist/)
   make harness-release-manifest VERSION=X.Y.Z PUBLISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
   # 4. Attach the manifest asset to the Release
   gh release upload vX.Y.Z dist/harness-release-vX.Y.Z.yaml
   ```

The manifest is generated under `dist/` (already git-ignored) so the release asset
— which carries a self-referential commit SHA — is never accidentally committed.
Delete any stray copy left in the repo root from an earlier run; the authoritative
copy lives on the GitHub Release.

The release manifest schema is `schemas/harness-release-v1.schema.json` (see
`docs/../schemas`). The deprecated `make template-release` target — which used to
auto-commit and auto-tag — now refuses to run and points here.

## The version bump is always a platform change

`pyproject.toml` and `uv.lock` are listed under `platform_paths` in
`adapters/registry.toml`, and step 1 of a release necessarily edits them. Every release
therefore reports `platform_change` when `BASE_REF` is passed. Verify the scope before
overriding:

```bash
make harness-platform-summary BASE_REF=<prev-tag>   # expect ONLY pyproject.toml + uv.lock
make harness-release-check VERSION=X.Y.Z BASE_REF=<prev-tag> ALLOW_PLATFORM=1
```

`ALLOW_PLATFORM=1` is justified only when the bump is the entire platform delta. Any
other platform path in that list is a genuine platform change and belongs in a separate
reviewed PR with a migration note.

## Recovering from a premature tag

A tag created before step 1 points at a commit whose `pyproject.toml` still holds the
previous version, so the preflight reports `tag_exists` alongside `version_mismatch`
and `changelog_missing`. All three share one cause: the tag ran ahead of the files.

Never resolve this by editing the files to match the tag. The recovery depends on
whether the tag was actually published (`gh release list`):

- **No GitHub Release and no downstream consumer** — the tag carries no contract yet.
  Delete it locally and on the remote, then restart at step 1:

  ```bash
  git tag -d vX.Y.Z
  git push origin :refs/tags/vX.Y.Z
  ```

  Deleting a remote tag is a repository-boundary operation: a human confirms and runs
  it, like every other publication step in this contract.

- **Already published or adopted downstream** — the tag is immutable. Leave it, and
  reconcile the files to the next version instead.

Pre-release tags (`vX.Y.Z-rc.N`) are outside this contract: the preflight, the sync
engine, and `make version` all expect plain `vX.Y.Z`. Avoid them, and clean up any
that exist so `git describe` stays meaningful.

## Proposing a change

Open a **Harness improvement proposal** issue (`.github/ISSUE_TEMPLATE/harness-improvement.yml`).
It is sanitized (no secrets, logs, local paths, or raw run data) and links to a
reviewed HEP proposal in the lab. Expected labels: `lab-proposal`,
`harness-governance` / `harness-platform`, `semver:patch|minor|major`,
`validation-required`.
