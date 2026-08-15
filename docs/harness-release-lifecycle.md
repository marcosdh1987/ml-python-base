# Harness release lifecycle (traceable release contract)

This template is the single authoritative source for shared governance (skills,
agents, governance docs, adapter templates). Downstream consumers — including the
`ai-agentic-harness-lab` — adopt it only as an **immutable SemVer tag**, never from
mutable `main`. The traceable release contract makes each release coherent and
machine-verifiable while keeping every repository-boundary operation manual.

## Principles

- **Read-only by default, guarded mutation.** `scripts/harness_release.py`
  validates, classifies, and prepares. Git mutation happens only inside the two
  guarded commands (`make release-pr`, `make publish-release`), each of which runs
  its full guard set first and then stops for an explicit confirmation.
- **Human-confirmed publication.** Nothing is tagged, pushed, or published without
  the operator answering the confirmation prompt (or deliberately passing `YES=1`).
  The printed-commands path (`make harness-release`) remains as a manual fallback.
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
| `make new-version [VERSION=X.Y.Z] [BASE_REF=…]` | Step 1: write the version into `pyproject.toml`, scaffold the CHANGELOG section from the commits since the last tag, refresh `uv.lock`. File-mutating but git-untouched; refuses non-increasing versions, existing tags, duplicate CHANGELOG sections, and scaffolding past a reconciled-but-untagged version. |
| `make release-pr [VERSION=…] [YES=1] [DRY_RUN=1]` | **Guarded.** Step 2: after curating the bullets — create `release/vX.Y.Z`, commit exactly the bump files, push, open the PR. Confirms before mutating. |
| `make publish-release [VERSION=…] [BASE_REF=…] [YES=1] [DRY_RUN=1]` | **Guarded.** Step 3, on `main` after the merge: full preflight, confirmation, then tag + push + GitHub Release (notes from the CHANGELOG section) + manifest + upload. |
| `make harness-change-summary [BASE_REF=…]` | Classify changes; recommend a bump. Warns about a pending (untagged) release. |
| `make harness-platform-summary [BASE_REF=…]` | Report platform changes + migration need. |
| `make harness-release-check [VERSION=…] [BASE_REF=…] [PROPOSAL=…] [ISSUE=…] [PR=…] [REQUIRE_PROVENANCE=1] [ALLOW_PLATFORM=1] [SKIP_GATES=1]` | Read-only preflight. |
| `make harness-release [VERSION=…]` | Manual fallback: preflight + print the publish steps without executing them. |
| `make harness-release-manifest VERSION=0.2.0 PUBLISHED_AT=<iso8601>` | Regenerate the release asset by hand **after** the tag exists (`publish-release` does this automatically). |

`VERSION` defaults to the version in `pyproject.toml` and `BASE_REF` to the latest
tag — with no arguments, every target acts on the release that is actually in flight.

The preflight verifies: valid SemVer; `pyproject.toml` and `CHANGELOG.md` agree with
the requested version; the tag does not already exist; a clean working tree;
governance/platform classification against `BASE_REF` (the `pyproject.toml` +
`uv.lock` pair — the bump itself — is auto-allowed; any other platform path fails);
and, when required, proposal/issue/PR provenance. It also runs `make check` and
`make check-sync` unless `SKIP_GATES=1`.

## Publishing a release

The tag is the **last** step. `pyproject.toml` and `CHANGELOG.md` define the version;
the tag only records a commit that already carries it. Creating the tag first inverts
that relationship and the preflight will reject the release — by design, since a
published tag is never moved.

```bash
# 1. Scaffold the bump (then curate the generated CHANGELOG bullets by hand)
make new-version
# 2. Branch + commit + push + open the release PR (asks for confirmation)
make release-pr
# ...review and merge the PR...
# 3. On main: preflight, confirmation, then tag + Release + manifest — all in one
git switch main && git pull
make publish-release
```

`publish-release` refuses to run off `main`, out of sync with `origin/main`, without
`gh`, or with a red preflight. It executes, in order: annotated tag → push tag →
`gh release create` (notes extracted from the `## [X.Y.Z]` CHANGELOG section) →
manifest generation (`published_at` stamped automatically) → `gh release upload`.
If a step fails mid-sequence, completed steps are **not** rolled back (a pushed tag
is immutable); the exact remaining commands are printed to finish by hand.

The fully manual path still exists: `make harness-release` prints the same command
sequence without executing anything.

The manifest is generated under `dist/` (already git-ignored) so the release asset
— which carries a self-referential commit SHA — is never accidentally committed.
Delete any stray copy left in the repo root from an earlier run; the authoritative
copy lives on the GitHub Release.

The release manifest schema is `schemas/harness-release-v1.schema.json` (see
`docs/../schemas`). The deprecated `make template-release` target — which used to
auto-commit and auto-tag — now refuses to run and points here.

## The version bump is a platform path — and auto-allowed

`pyproject.toml` and `uv.lock` are listed under `platform_paths` in
`adapters/registry.toml`, and step 1 of a release necessarily edits them. The preflight
recognizes this: when the platform delta since the base tag is **exactly** that pair,
it prints an auto-allow note instead of failing. That automates the manual
`harness-platform-summary` verification this section used to prescribe.

Any *other* platform path is still a genuine platform change: the preflight fails, and
that work belongs in a separate reviewed PR with a migration note. `ALLOW_PLATFORM=1`
exists for that reviewed case only — never to silence the check.

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

## Testing the release flow

`tests/harness_release/test_harness_release.py` exercises the whole contract against
miniature repos built in `tmp_path`. Two environments meet there and must both be
hermetic:

- Git commands run **by the tests** go through the `_git` helper, which injects a
  throwaway identity via environment variables and masks global/system config.
- Git commands run **by the script under test** (`scripts/harness_release.py` — e.g.
  the real `git tag -a` in the publish tests) inherit the actual process
  environment. On a CI runner there is no global config and no usable
  auto-detected identity, so the fixtures persist `user.name`/`user.email` in each
  temp repo's local config (`_configure_identity`). Without that, publish tests
  pass locally (git auto-detects an identity from the OS user) but fail in CI with
  `fatal: empty ident name`.

To reproduce the CI conditions locally:

```bash
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=user.useConfigOnly GIT_CONFIG_VALUE_0=true \
uv run pytest tests/harness_release/ --no-cov
```

## Proposing a change

Open a **Harness improvement proposal** issue (`.github/ISSUE_TEMPLATE/harness-improvement.yml`).
It is sanitized (no secrets, logs, local paths, or raw run data) and links to a
reviewed HEP proposal in the lab. Expected labels: `lab-proposal`,
`harness-governance` / `harness-platform`, `semver:patch|minor|major`,
`validation-required`.
