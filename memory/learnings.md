# Learnings

> Non-obvious facts discovered while working: gotchas, why-it-is-this-way, dead ends
> to avoid. Append new entries at the top. One fact per entry.

## OpenCode gateway model ids mirror LiteLLM aliases — 2026-06-23

When LiteLLM exposes a model as `model_name: nim-*`, OpenCode should list the key
under `provider.gateway.models` without the provider prefix and select it as
`gateway/<model_name>` in `.env`. The NVIDIA API key stays in the gateway config;
the repo only needs `GATEWAY_BASE_URL` and `GATEWAY_TOKEN`.

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
