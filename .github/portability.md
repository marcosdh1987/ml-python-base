# Runtime Portability and Model Tiers

> Status: **Both runtimes are LIVE.** Claude Code emits a `model:` alias into each
> `.claude/agents/<name>.md` by tier (planning/review on the flagship, execution on
> Sonnet to save tokens). **OpenCode is operational too**: `opencode.json` ships
> env-driven providers for Ollama / LM Studio (self-hosted) plus built-in OpenAI and
> OpenCode Zen, configured entirely through `.env` — no IPs or keys are committed.

## Why tiers, not model ids

Agents (`.github/agents/`) and skills reference a **tier**
(`planner` / `executor` / `fast`), never a concrete model id. Switching runtime is
then a one-table change: the same governed agent maps to `claude-opus` on Claude
Code and to a self-hosted `qwen`/`llama` on OpenCode.

| Tier       | Role in the SDLC                         | min context | Claude Code (live alias) | OpenCode self-hosted (intended) |
|------------|------------------------------------------|-------------|--------------------------|---------------------------------|
| `planner`  | orchestrator, planner, reviewer          | large       | `opus`                   | `qwen2.5-coder:32b`             |
| `executor` | implementer, tester                      | medium      | `sonnet`                 | `qwen2.5-coder:14b`             |
| `fast`     | documenter, quick edits                  | small       | `haiku`                  | `llama3.1:8b`                   |

The Claude column uses **aliases** (`opus`/`sonnet`/`haiku`), not pinned ids, so each
agent always resolves to whatever that tier's current model is — "el que esté
disponible". The mapping lives in `src/ml_python_base/skills_sync/agents.py`
(`_CLAUDE_TIER_MODEL`). The exact local models are placeholders — pick what your
hardware runs. Keep the **tier names** stable; only the right-hand mapping changes
per runtime.

## OpenCode config (operational, env-driven)

`opencode.json` ships with the providers wired and **every host/model behind
`{env:...}` interpolation**, so the template carries no IPs or keys — you set them
in `.env` (gitignored). Providers:

- `ollama` / `lmstudio` — custom OpenAI-compatible providers; `baseURL` comes from
  `OLLAMA_BASE_URL` / `LMSTUDIO_BASE_URL`.
- `openai` and `opencode` (OpenCode Zen) — built-in; authenticate with
  `opencode auth login` (keychain) or `OPENAI_API_KEY`.

Tiering is two levels via `model` (main) + `small_model` (lightweight), both from
`.env` (`OPENCODE_MODEL`, `OPENCODE_SMALL_MODEL`). A single local GPU rarely runs
three large models at once, so per-agent 3-tier splitting is intentionally not
forced here; switch the active model anytime with `/models` in the TUI.

### Setup from the CLI

```bash
brew install anomalyco/tap/opencode   # recommended tap (most up to date)
cp .env.example .env                  # then edit OLLAMA_BASE_URL / LMSTUDIO_BASE_URL / OPENCODE_MODEL
make opencode-doctor                  # check install + that the endpoints answer
make opencode                         # launch the TUI with .env loaded
```

Inside the TUI: `/connect` to add a cloud provider (OpenAI / Zen) and paste its key,
`/models` to switch the active model. `make opencode` loads `.env` for you; for direct
`opencode` use, load it yourself (`direnv`, or `set -a; . ./.env; set +a`) so the
`{env:...}` values resolve.

> LM Studio model ids: the placeholder `local-model` under `provider.lmstudio.models`
> in `opencode.json` must match the id LM Studio serves (Developer/Server tab).

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

## Activation checklist

1. Install and start Ollama / LM Studio on your GPU host(s); pull the models you set
   in `.env` (`ollama pull qwen2.5-coder:32b`, or load a model in LM Studio).
2. `cp .env.example .env` and set `OLLAMA_BASE_URL` / `LMSTUDIO_BASE_URL` /
   `OPENCODE_MODEL` / `OPENCODE_SMALL_MODEL`. For LM Studio, also list its served
   model id under `provider.lmstudio.models` in `opencode.json`.
3. `make opencode-doctor` — confirms opencode is installed and each endpoint answers.
4. `make opencode` — run a small task through OpenCode and confirm each SDLC gate
   (`make check`) still passes on the local model.
