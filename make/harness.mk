# =============================================================================
# Traceable harness release contract (scripts/harness_release.py).
#
# Read-only by default: targets validate, classify, and prepare. The ONLY two
# mutation points are `release-pr` and `publish-release` — each runs its full
# guard set first and then asks for an explicit confirmation (YES=1 skips the
# prompt; DRY_RUN=1 prints the plan and executes nothing). Included from the
# root Makefile. See docs/harness-release-lifecycle.md.
#
# The whole flow:
#   make new-version        # scaffold the bump (edit the CHANGELOG bullets!)
#   make release-pr         # guard -> confirm -> branch+commit+push+PR
#   ...merge the PR...
#   make publish-release    # on main: preflight -> confirm -> tag+Release+manifest
# =============================================================================

HARNESS_RELEASE = uv run python scripts/harness_release.py

# Show the current version at a glance: pyproject (source of truth), the latest
# published tag, and whether the current version is already released or pending.
version:
	@ver=$$(grep -m1 '^version' pyproject.toml | sed -E 's/.*"(.*)".*/\1/'); \
	tag=$$(git describe --tags --abbrev=0 2>/dev/null || echo "(none)"); \
	echo "📦 pyproject version : $$ver"; \
	echo "🏷️  latest tag        : $$tag"; \
	if git rev-parse "v$$ver" >/dev/null 2>&1; then \
		echo "✅ v$$ver is published."; \
	else \
		echo "⚠️  v$$ver is NOT tagged yet — release pending (run 'make publish-release' on main)."; \
	fi

# Step 2 in one command: write VERSION into pyproject.toml, scaffold the
# CHANGELOG section from the commits since the last tag, refresh uv.lock, and
# point at `make release-pr`. Mutates FILES only — git stays untouched here.
# Refuses to scaffold past a reconciled-but-untagged version (pending release).
# Usage: make new-version [VERSION=0.4.0] [BASE_REF=v0.3.0]
#        (no VERSION: uses the recommended bump since the latest tag)
new-version:
	@$(HARNESS_RELEASE) prepare \
		$(if $(VERSION),--version $(VERSION),) \
		$(if $(BASE_REF),--base-ref $(BASE_REF),)
	@echo "🔒 Refreshing uv.lock..."
	@uv lock -q
	@echo "✅ uv.lock refreshed."

# Guarded step: after you curated the CHANGELOG bullets, create the release
# branch, commit exactly the bump files (pyproject.toml, CHANGELOG.md, uv.lock),
# push, and open the PR. Confirms before mutating.
# Usage: make release-pr [VERSION=0.5.0] [YES=1] [DRY_RUN=1]
release-pr:
	@$(HARNESS_RELEASE) release-pr \
		$(if $(VERSION),--version $(VERSION),) \
		$(if $(YES),--yes,) \
		$(if $(DRY_RUN),--dry-run,)

# Guarded step: on main, after the release PR merged. Full preflight (incl.
# gates), then — after confirmation — tag, push the tag, create the GitHub
# Release (notes = the CHANGELOG section), generate the manifest, upload it.
# Usage: make publish-release [VERSION=0.5.0] [BASE_REF=v0.4.0] [YES=1] [DRY_RUN=1] \
#            [PROPOSAL=...] [ISSUE=...] [PR=...] [MIGRATION=docs/...] [BREAKING=1] \
#            [REQUIRE_PROVENANCE=1] [ALLOW_PLATFORM=1] [SKIP_GATES=1]
publish-release:
	@$(HARNESS_RELEASE) publish \
		$(if $(VERSION),--version $(VERSION),) \
		$(if $(BASE_REF),--base-ref $(BASE_REF),) \
		$(if $(PROPOSAL),--proposal $(PROPOSAL),) \
		$(if $(ISSUE),--issue $(ISSUE),) \
		$(if $(PR),--pr $(PR),) \
		$(if $(MIGRATION),--migration $(MIGRATION),) \
		$(if $(BREAKING),--breaking,) \
		$(if $(REQUIRE_PROVENANCE),--require-provenance,) \
		$(if $(ALLOW_PLATFORM),--allow-platform,) \
		$(if $(SKIP_GATES),--skip-gates,) \
		$(if $(YES),--yes,) \
		$(if $(DRY_RUN),--dry-run,)

# Classify governance vs platform changes since BASE_REF and recommend a bump.
# Usage: make harness-change-summary [BASE_REF=v0.1.0]   (default: latest tag)
harness-change-summary:
	@$(HARNESS_RELEASE) change-summary \
		$(if $(BASE_REF),--base-ref $(BASE_REF),)

# Identify platform changes and the migration note they require.
# Usage: make harness-platform-summary [BASE_REF=v0.1.0]   (default: latest tag)
harness-platform-summary:
	@$(HARNESS_RELEASE) platform-summary \
		$(if $(BASE_REF),--base-ref $(BASE_REF),)

# Read-only release preflight: SemVer, version/changelog match, tag collision,
# clean tree, governance/platform classification, provenance, and gates.
# The pyproject.toml + uv.lock pair (the bump itself) is auto-allowed.
# Usage: make harness-release-check [VERSION=0.2.0] [BASE_REF=v0.1.0] \
#            [PROPOSAL=HEP-2026-014] [ISSUE=owner/repo#31] [PR=owner/repo#32] \
#            [REQUIRE_PROVENANCE=1] [ALLOW_PLATFORM=1] [SKIP_GATES=1]
#        (defaults: VERSION from pyproject.toml, BASE_REF from the latest tag)
harness-release-check:
	@$(HARNESS_RELEASE) release-check \
		$(if $(VERSION),--version $(VERSION),) \
		$(if $(BASE_REF),--base-ref $(BASE_REF),) \
		$(if $(PROPOSAL),--proposal $(PROPOSAL),) \
		$(if $(ISSUE),--issue $(ISSUE),) \
		$(if $(PR),--pr $(PR),) \
		$(if $(REQUIRE_PROVENANCE),--require-provenance,) \
		$(if $(ALLOW_PLATFORM),--allow-platform,) \
		$(if $(SKIP_GATES),--skip-gates,)

# Generate the release manifest asset AFTER the tag exists. (publish-release
# does this for you; keep this target for regenerating an asset by hand.)
# Usage: make harness-release-manifest VERSION=0.2.0 PUBLISHED_AT=2026-07-22T15:00:00Z \
#            [PROPOSAL=HEP-2026-014] [ISSUE=...] [PR=...] [MIGRATION=docs/...] [BREAKING=1]
harness-release-manifest:
	@[ -n "$(VERSION)" ] || { echo "❌ VERSION is required. Example: VERSION=0.2.0"; exit 1; }
	@[ -n "$(PUBLISHED_AT)" ] || { echo "❌ PUBLISHED_AT is required (ISO-8601)."; exit 1; }
	@$(HARNESS_RELEASE) release-manifest --version $(VERSION) --published-at $(PUBLISHED_AT) \
		$(if $(PROPOSAL),--proposal $(PROPOSAL),) \
		$(if $(ISSUE),--issue $(ISSUE),) \
		$(if $(PR),--pr $(PR),) \
		$(if $(MIGRATION),--migration $(MIGRATION),) \
		$(if $(BREAKING),--breaking,)

# Manual fallback: run the preflight and PRINT the exact publish commands
# without executing anything. `make publish-release` is the guarded automation.
# Usage: make harness-release [VERSION=0.2.0] [BASE_REF=v0.1.0] [SKIP_GATES=1]
harness-release:
	@$(HARNESS_RELEASE) release \
		$(if $(VERSION),--version $(VERSION),) \
		$(if $(BASE_REF),--base-ref $(BASE_REF),) \
		$(if $(PROPOSAL),--proposal $(PROPOSAL),) \
		$(if $(ISSUE),--issue $(ISSUE),) \
		$(if $(PR),--pr $(PR),) \
		$(if $(REQUIRE_PROVENANCE),--require-provenance,) \
		$(if $(ALLOW_PLATFORM),--allow-platform,) \
		$(if $(SKIP_GATES),--skip-gates,)

.PHONY: version new-version release-pr publish-release \
	harness-change-summary harness-platform-summary \
	harness-release-check harness-release-manifest harness-release
