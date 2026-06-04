# Runtime Portability and Model Tiers (design)

> Status: **design + documentation only.** The tier tables and provider config
> below are the intended wiring for falling back from Claude Code to self-hosted
> models via OpenCode (Ollama / LM Studio). They are not yet activated in
> `opencode.json`; activate them when you need the fallback.

## Why tiers, not model ids

Agents (`.github/agents/`) and skills reference a **tier**
(`planner` / `executor` / `fast`), never a concrete model id. Switching runtime is
then a one-table change: the same governed agent maps to `claude-opus` on Claude
Code and to a self-hosted `qwen`/`llama` on OpenCode.

| Tier       | Role in the SDLC                         | min context | Claude Code (today) | OpenCode self-hosted (intended) |
|------------|------------------------------------------|-------------|---------------------|---------------------------------|
| `planner`  | orchestrator, planner, reviewer          | large       | `claude-opus-4-8`   | `qwen2.5-coder:32b`             |
| `executor` | implementer, tester                      | medium      | `claude-sonnet-4-6` | `qwen2.5-coder:14b`             |
| `fast`     | documenter, quick edits                  | small       | `claude-haiku-4-5`  | `llama3.1:8b`                   |

The exact local models are placeholders — pick what your hardware runs. Keep the
**tier names** stable; only the right-hand mapping changes per runtime.

## Intended `opencode.json` providers (not yet applied)

Ollama and LM Studio both expose an OpenAI-compatible API, so they slot in as
custom providers. When activating the fallback, extend `opencode.json` along these
lines (illustrative):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": "OPENCODE.md",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": { "qwen2.5-coder:32b": {}, "qwen2.5-coder:14b": {}, "llama3.1:8b": {} }
    },
    "lmstudio": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:1234/v1" },
      "models": { "local-model": {} }
    }
  }
}
```

A future `make opencode-doctor` target should verify the endpoint is reachable and
the referenced models are pulled before a session relies on them.

## Graceful degradation for small context windows

Local models usually have smaller context windows than Claude. The lifecycle is
designed to survive this:

- **Fresh context per phase.** The `orchestrator` delegates each SDLC phase to a
  separate agent, so no single context must hold the whole task — the biggest
  token saver when moving to local models.
- **`context_budget` on agents.** Agents declare `small` / `medium` / `large`. A
  projector may drop or down-tier `large`-only agents when the active runtime's
  models cannot satisfy `min context`.
- **Skill degradation.** Long skills can document a shorter "degraded mode" path
  for small-window runtimes.

## Activation checklist (when you need the fallback)

1. Install and start Ollama or LM Studio; pull the models for each tier.
2. Apply the provider block above to `opencode.json`; map agents' tiers to models.
3. Add `make opencode-doctor` to verify endpoint + pulled models.
4. Run a small task through OpenCode and confirm each SDLC gate still passes.
