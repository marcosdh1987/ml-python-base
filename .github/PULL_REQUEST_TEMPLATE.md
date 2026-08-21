## What changed

<!-- One or two sentences. What does this PR do, and why? -->

## Why

<!-- The problem being solved. Link the issue or ADR if there is one. -->

## Verification

<!-- What did you actually run? Paste the result, not the intention. -->

- [ ] `make ci` passes locally (check + check-sync + check-docs-coverage)
- [ ] Changes under `src/` or `tests/` ship with a `docs/` update
- [ ] Governed sources edited (`.github/skills/`, `.github/agents/`, `adapters/`),
      not the generated copies — and `make sync-skills` was run if so
- [ ] Any new external skill declares `upstream` and `license` in
      `adapters/registry.toml` and is attributed in `NOTICE`

## Notes for the reviewer

<!-- Trade-offs, things you are unsure about, follow-ups deliberately left out. -->
