# =============================================================================
# Traceable harness release contract (scripts/harness_release.py).
#
# All targets are READ-ONLY: they validate, classify, and prepare. Tagging,
# pushing, and GitHub Release publication stay manual. Included from the root
# Makefile. See docs/harness-release-lifecycle.md.
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
		echo "⚠️  v$$ver is NOT tagged yet — release pending (see 'make harness-release VERSION=$$ver')."; \
	fi

# Classify governance vs platform changes since BASE_REF and recommend a bump.
# Usage: make harness-change-summary BASE_REF=v0.1.0
harness-change-summary:
	@[ -n "$(BASE_REF)" ] || { echo "❌ BASE_REF is required. Example: BASE_REF=v0.1.0"; exit 1; }
	@$(HARNESS_RELEASE) change-summary --base-ref $(BASE_REF)

# Identify platform changes and the migration note they require.
# Usage: make harness-platform-summary BASE_REF=v0.1.0
harness-platform-summary:
	@[ -n "$(BASE_REF)" ] || { echo "❌ BASE_REF is required. Example: BASE_REF=v0.1.0"; exit 1; }
	@$(HARNESS_RELEASE) platform-summary --base-ref $(BASE_REF)

# Read-only release preflight: SemVer, version/changelog match, tag collision,
# clean tree, governance/platform classification, provenance, and gates.
# Usage: make harness-release-check VERSION=0.2.0 [BASE_REF=v0.1.0] \
#            [PROPOSAL=HEP-2026-014] [ISSUE=owner/repo#31] [PR=owner/repo#32] \
#            [REQUIRE_PROVENANCE=1] [ALLOW_PLATFORM=1] [SKIP_GATES=1]
harness-release-check:
	@[ -n "$(VERSION)" ] || { echo "❌ VERSION is required. Example: VERSION=0.2.0"; exit 1; }
	@$(HARNESS_RELEASE) release-check --version $(VERSION) \
		$(if $(BASE_REF),--base-ref $(BASE_REF),) \
		$(if $(PROPOSAL),--proposal $(PROPOSAL),) \
		$(if $(ISSUE),--issue $(ISSUE),) \
		$(if $(PR),--pr $(PR),) \
		$(if $(REQUIRE_PROVENANCE),--require-provenance,) \
		$(if $(ALLOW_PLATFORM),--allow-platform,) \
		$(if $(SKIP_GATES),--skip-gates,)

# Generate the release manifest asset AFTER the tag exists.
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

# Run the preflight and PRINT the exact manual tag/release commands. No git mutation.
# Usage: make harness-release VERSION=0.2.0 [BASE_REF=v0.1.0] [SKIP_GATES=1]
harness-release:
	@[ -n "$(VERSION)" ] || { echo "❌ VERSION is required. Example: VERSION=0.2.0"; exit 1; }
	@$(HARNESS_RELEASE) release --version $(VERSION) \
		$(if $(BASE_REF),--base-ref $(BASE_REF),) \
		$(if $(PROPOSAL),--proposal $(PROPOSAL),) \
		$(if $(ISSUE),--issue $(ISSUE),) \
		$(if $(PR),--pr $(PR),) \
		$(if $(REQUIRE_PROVENANCE),--require-provenance,) \
		$(if $(ALLOW_PLATFORM),--allow-platform,) \
		$(if $(SKIP_GATES),--skip-gates,)

.PHONY: version harness-change-summary harness-platform-summary harness-release-check \
	harness-release-manifest harness-release
