# Local Model on Your Mac (LM Studio -> LiteLLM -> OpenCode)

The install path. Go from a fresh clone to `make opencode` running against a model served
on your own Mac, so day-to-day coding costs no cloud tokens. Written for a developer who
has never served a local model.

This doc covers **how to get it running and which knob lives where**. It deliberately does
**not** repeat the tuning rationale: every "why this number" question is answered in
[`docs/local-model-runtime-config.md`](local-model-runtime-config.md) — the hard levers
(output cap, served context, repetition penalty, one increment per chat, minimal
instruction surface) and the honest ceiling of a small model. Read that one once; this one
you follow step by step.

> **Placeholders.** The shared gateway is not deployed yet, so no real model or card names
> appear below. These are the only values you have to fill in:
>
> - Step 2 (from the model list you were given):
>   `<LMSTUDIO_MODEL_NAME_16GB>`, `<LMSTUDIO_MODEL_NAME_24GB>`
> - Step 3 (read off your own server): `<LMSTUDIO_MODEL_ID>`
> - Step 4 (names you choose, in `gateway/config.yaml`): `<BUILD_CARD>`, `<PLAN_CARD>`,
>   `<SMALL_CARD>`, `<PLAN_PROVIDER>`, `<PLAN_MODEL_ID>`, `<PLAN_PROVIDER_API_KEY>`
> - Step 5 (the same card names, in `.env`)

## Memory budget — pick your tier first

Everything else depends on this, so decide it before downloading anything. A model does
not fit in "16 GB of RAM" — it fits in what is left after macOS, your editor, a browser,
and (if you use it) Docker Desktop:

| Your Mac | Docker Desktop also running? | Realistic budget for weights + KV cache |
|---|---|---|
| 16 GB | yes | **~9-10 GB** |
| 16 GB | no | ~11-12 GB |
| 24 GB | yes | ~16-17 GB |
| 24 GB | no | ~18-19 GB |

Two things that budget has to cover:

- **The weights** — the download size of the quantized model, roughly.
- **The KV cache** — the served context window, allocated separately. At 32k it costs
  **another ~2-3 GB** for a model this size. It is not free and it is not part of the
  download size.

So on a 16 GB Mac with Docker running, a model whose weights alone are 9 GB does not fit
at 32k context. Subtract the KV cache first, then pick the quant. LM Studio shows its own
estimate at load time — trust that over any arithmetic here.

Honest version: on 16 GB, if you need Docker Desktop *and* a local model at the same time,
the model is what gets cut. Either stop Docker while you code, or accept the smaller tier.
Pushing past the budget does not error — macOS swaps, and generation slows to the point of
being unusable.

## The path, in order

### 1. Install LM Studio

```bash
brew install --cask lm-studio
```

Or download the `.dmg` from <https://lmstudio.ai>. Open it once so it finishes setup.

### 2. Download the model for your tier

In LM Studio, open the **Discover** tab and search for the model matching your budget from
the table above:

- 16 GB tier: `<LMSTUDIO_MODEL_NAME_16GB>`
- 24 GB tier: `<LMSTUDIO_MODEL_NAME_24GB>`

Download and wait — these are multi-gigabyte files.

### 3. Configure and start the server

Still in LM Studio, open the **Developer** (server) tab, select the model, and set these in
the model's **load settings** before loading it:

| Setting | Value | Why |
|---|---|---|
| Context Length | **32768** minimum | This is the KV cache. Below 32k the workflow stops working — lever 2. |
| Temperature | 0.2 | Deterministic edits — lever 6. |
| Repeat Penalty | 1.15 | The fix for infinite repetition loops — lever 6. |

Load the model, then **Start Server** on port `1234`. Confirm what it actually serves:

```bash
curl -s http://localhost:1234/v1/models | python3 -m json.tool
```

The `id` in that response is your `<LMSTUDIO_MODEL_ID>`. Copy it exactly — a near-miss here
is the most common cause of a gateway that answers but never returns a completion.

### 4. Start the local gateway

The gateway is LiteLLM. It is what enforces the output cap and the sampling settings no
matter which client talks to it, and what makes every call traceable.

```bash
cp gateway/config.example.yaml gateway/config.yaml
# edit gateway/config.yaml: replace every <PLACEHOLDER>, including <LMSTUDIO_MODEL_ID>
LITELLM_MASTER_KEY=sk-local-change-me \
  uvx --from 'litellm[proxy]' --with 'fastapi==0.140.0' \
  litellm --config gateway/config.yaml --port 4000
```

Expect `Application startup complete.` and `Uvicorn running on http://0.0.0.0:4000`. Leave
it running in its own terminal. `gateway/config.yaml` is gitignored; the committed template
is `gateway/config.example.yaml`.

> **Why the `fastapi` pin.** `litellm[proxy]` declares `fastapi>=0.136.3,<1.0`, but its
> proxy code imports `get_flat_dependant`, which FastAPI removed during the 0.140 patch
> series. Without the pin the proxy dies at startup with
> `ImportError: cannot import name 'get_flat_dependant' from 'fastapi.dependencies.utils'`
> — verified against litellm 1.95.0 / fastapi 0.141.1. Drop the `--with` flag once upstream
> tightens that range; the symptom if you drop it too early is that exact ImportError.

Run it natively like this rather than in a container: it costs ~200-300 MB, while Docker
Desktop costs 2-4 GB of the budget you just measured in the table above. On 16 GB that
difference is a whole model tier.

> **Already running Docker?** You can run the same image with
> `docker run -p 4000:4000 -v $(pwd)/gateway/config.yaml:/app/config.yaml -e LITELLM_MASTER_KEY=sk-local-change-me ghcr.io/berriai/litellm:main-latest --config /app/config.yaml --port 4000`.
> One change is required: from inside the container, LM Studio is not on `localhost`. Set
> `LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1` for the gateway process.

### 5. Fill in `.env`

```bash
cp .env.example .env   # only if you don't have one yet
```

Five lines matter:

```bash
OPENCODE_MODEL=gateway/<BUILD_CARD>
OPENCODE_MODEL_PLAN=gateway/<PLAN_CARD>
GATEWAY_BASE_URL=http://localhost:4000/v1
GATEWAY_TOKEN=sk-local-change-me
LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

`GATEWAY_TOKEN` must equal the `LITELLM_MASTER_KEY` you started the gateway with in step 4.
`GATEWAY_BASE_URL` must end in `/v1`.

### 6. Check the wiring

```bash
make opencode-doctor
```

Expect:

```text
✅ opencode: <version>
✅ LM_Studio reachable: http://localhost:1234/v1
✅ AI Gateway reachable: http://localhost:4000/v1
```

`–  Ollama: not configured in .env` is fine — this path does not use Ollama.

**The doctor proves reachability, not correctness.** It never checks that the card named in
`OPENCODE_MODEL` exists in your gateway, and it always exits 0. Cross-check by hand:

```bash
set -a; . ./.env; set +a
curl -s "$GATEWAY_BASE_URL/models" -H "Authorization: Bearer $GATEWAY_TOKEN" \
  | python3 -m json.tool
```

Every card you configured must appear, with the context you declared:

```json
{"data": [{"id": "<BUILD_CARD>", "object": "model", "max_input_tokens": 32768}]}
```

A card missing from that list is a card OpenCode cannot use, whatever `.env` says — the
name in `.env` does not match `model_name` in `gateway/config.yaml`, or the gateway skipped
that deployment at startup (check its log).

### 7. Warm up, then work

Run the warmup request from *Warm the model before you start* below, then:

```bash
make opencode
```

Plan mode is the strong model, `Tab` switches to Build on your local model. The loop itself
is in [`docs/opencode-workflow.md`](opencode-workflow.md).

## Environment variable contract

Defaults come from [`.env.example`](../.env.example). Once the placeholders are real, this
set works end to end with no edits — the only reasons to change anything are different
hardware or a port already in use.

| Variable | Default | What it controls | Change it when |
|---|---|---|---|
| `OPENCODE_MODEL` | `gateway/<BUILD_CARD>` | The card the **build** agent uses — the one that writes code. | You want a different local tier (a faster, smaller card). |
| `OPENCODE_MODEL_PLAN` | `gateway/<PLAN_CARD>` | The card the **plan** agent uses (`Tab` switches). | You want to plan locally too — see *Plan cloud, build local*. |
| `OPENCODE_SMALL_MODEL` | `gateway/<SMALL_CARD>` | Cheap background calls (chat titles, trivia). Never writes code. | Rarely. Leave it. |
| `GATEWAY_BASE_URL` | `http://localhost:4000/v1` | Where your LiteLLM listens. Must end in `/v1`. | Port 4000 is taken — change here **and** in `--port`. |
| `GATEWAY_TOKEN` | `sk-local-change-me` | Auth to your gateway. Must equal `LITELLM_MASTER_KEY`. | Always, if the gateway is reachable by anything but you. |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | Where LM Studio listens. Drives the doctor check and the card's `api_base`. | LM Studio is on another port, another Mac, or you run the gateway in Docker. |

Timeouts are **not** environment variables — they live in the card. See the ownership table
below. The two you may need are `timeout` (whole request, default 600s in the template) and
`stream_timeout` (stall between streamed chunks, 120s).

### If your hardware differs

- **Less RAM than the tier.** Drop to a smaller quant. Do **not** drop the served context
  below 32k to make room — under 32k the harness levers stop being able to help, and you
  get truncation instead of a smaller model.
- **More RAM.** Raise Context Length toward 64k in LM Studio, and raise `max_input_tokens`
  in the card **to match, never above**. Leave `max_tokens` (the output cap) where it is —
  more context does not mean you want longer answers.
- **LM Studio elsewhere** (another port, another Mac on the LAN). Change
  `LMSTUDIO_BASE_URL` in `.env`. The card reads `api_base: os.environ/LMSTUDIO_BASE_URL`,
  so one value drives both — but the gateway process must see that value in its own
  environment.
- **Port 4000 already in use.** Change `GATEWAY_BASE_URL` and the `--port` flag together.
  They must agree or the doctor fails.

## Who owns which knob

The single most confusing part of this setup: the knobs live in three different places, and
only one of them is an environment variable.

| Knob | Where it is set | Env var? |
|---|---|---|
| Context window (KV cache) | LM Studio load settings / Ollama `num_ctx` | **No — it is a serving decision** |
| Declared `max_input_tokens` | `model_info` on the card | Via yaml |
| Output cap | `max_tokens` on the card | Via yaml |
| Temperature / repetition penalty | The card | Via yaml |
| Request / stream timeout | The card (`timeout`, `stream_timeout`) + `general_settings` | Via yaml |
| Which card is used | `.env` -> `OPENCODE_MODEL` | **Yes** |

**The context window cannot be adjusted from the gateway or by any environment variable.**
It is allocated when LM Studio loads the model, and nothing downstream can grow it. The
card's `max_input_tokens` is only a *declaration* — it tells clients how much they may
send. It does not reserve anything.

That gap is the trap: **if LM Studio serves less than the card declares, the model
truncates silently and starts looping.** No error is raised anywhere. The gateway happily
forwards a 32k prompt to a server pinned at 8k, and what comes back is a model that has
lost the beginning of its own instructions. Keep the two numbers equal. When you are not
sure what LM Studio is actually serving, lower the card.

## Warm the model before you start

The first request after starting LM Studio triggers a just-in-time load of several
gigabytes from disk. That load happens *inside* your first request, so it can consume the
entire timeout and surface as a broken gateway — when the gateway is fine and the model was
merely cold.

Fire one throwaway request after step 4, before you open OpenCode:

```bash
set -a; . ./.env; set +a
curl -s "$GATEWAY_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $GATEWAY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"model":"<BUILD_CARD>","messages":[{"role":"user","content":"ok"}],"max_tokens":8}'
```

The first run may take minutes. Every run after it returns in seconds — that is how you know
the model is resident. Warm up again after LM Studio unloads the model on its idle timer,
and after any model swap.

## Plan cloud, build local

The split exists because planning and executing fail differently. Planning needs breadth
across files; executing needs a small, well-scoped edit. A local model is good at the
second long before it is good at the first.

**Plan with a strong cloud model when** the change spans several files, the design is not
settled yet, or you need a backlog broken into increments small enough for the local model
to chew one at a time. The spend is small — plans are short.

**The local model is enough for both when** the work is single-file and mechanical, the bug
already has a known cause, or you are writing tests and docs for code that already exists.
Point both at the same card and stay entirely offline:

```bash
OPENCODE_MODEL_PLAN=gateway/<BUILD_CARD>
```

One caveat, already documented in [`.env.example`](../.env.example): a strong planner
writes steps that assume a strong executor, and a small local model then cannot execute
them. If you plan with a cloud model, insist on small increments in the plan itself.
Sizing heuristics are in [`docs/task-sizing.md`](task-sizing.md); the `Tab` mechanics are
in [`docs/opencode-workflow.md`](opencode-workflow.md).

## Troubleshooting

| Symptom | Actual cause | Fix |
|---|---|---|
| `Response too long` / the response hit the length limit | The output cap never reached the request. | `max_tokens` is missing from the card — or you edited `config.example.yaml` and the gateway is running `config.yaml`. Restart the gateway after editing. See lever 1. |
| The same sentence or decision repeats until the turn dies | A decoding pathology, not a reasoning failure. **No instruction can fix it** — a model stuck in a loop cannot obey "stop repeating". | Set `repetition_penalty` on the card (and Repeat Penalty in LM Studio). Low temperature alone makes it *worse*. See lever 6. |
| Long "what's implemented / what's missing" summaries; the model has lost the code state | The conversation got compacted — it ran too many increments. | Start a fresh chat per increment. The long conversation *is* the problem. See lever 5. |
| Timeout or hang on the first prompt of the session | Cold model: a multi-gigabyte JIT load is happening inside your request. | Send the warmup request first. If it still times out on a warm model, raise `timeout` on the card. See *Warm the model*. |
| `make opencode-doctor` is green but OpenCode errors on the model | The doctor never validates the card name — it only pings `/models`. | Run the `curl "$GATEWAY_BASE_URL/models"` cross-check from step 6 and match `model_name` in `gateway/config.yaml` exactly. |
| The model truncates mid-file, or loses the thread far earlier than expected | LM Studio is serving less context than the card declares. Truncation is silent. | Make Context Length (LM Studio) and `max_input_tokens` (card) equal. See *Who owns which knob*. |
| The gateway will not start: `ImportError: cannot import name 'get_flat_dependant'` | `litellm[proxy]` resolved a FastAPI newer than its own code supports. | Add `--with 'fastapi==0.140.0'` to the `uvx` command. See step 4. |
| The gateway starts, but one card is missing from `/v1/models` and the log shows `LLM Provider NOT provided` | That card still has an unreplaced `<PLACEHOLDER>` in `litellm_params.model`. LiteLLM skips the bad deployment and boots anyway. | Replace the placeholder in `gateway/config.yaml` and restart. |
| Generation is correct but extremely slow, and the Mac is unresponsive | The model plus KV cache exceeded your budget and macOS is swapping. | Quit Docker Desktop, or drop to the smaller tier. See *Memory budget*. |

## See also

- [`docs/local-model-runtime-config.md`](local-model-runtime-config.md) — the mechanical
  layer this guide installs: why the output cap, the served context, and the repetition
  penalty are the levers that matter, and the honest ceiling of a small model.
- [`docs/opencode-workflow.md`](opencode-workflow.md) — the plan/build `Tab` loop and which
  skill runs in which mode.
- [`docs/task-sizing.md`](task-sizing.md) — how big a chunk this model can actually take.
- [`LOCAL_AGENT.md`](../LOCAL_AGENT.md) — the short always-loaded operating contract for
  the `local_model_32k` mode.
- [`.env.example`](../.env.example) — every variable, with the alternatives commented out.
- [`gateway/config.example.yaml`](../gateway/config.example.yaml) — the gateway template
  copied in step 4.
