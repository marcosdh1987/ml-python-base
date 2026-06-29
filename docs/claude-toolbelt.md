# Claude Toolbelt

This repository expects Claude to use available tools before asking the user for
operational or repository facts. The toolbelt is the practical layer for that:
MCP servers, CLIs, Make targets, and local service endpoints that can answer
routine questions directly.

## Current MCP Servers

The checked-in `.mcp.json` keeps the default MCP surface small:

| Server | Purpose | Typical use |
|--------|---------|-------------|
| `context7` | Current library documentation | Dependency APIs, migration notes, setup details |
| `git` | Structured repository inspection | History, diffs, branches, file state |

Use `.mcp.example.json` as the expansion template. It includes optional examples
for GitHub, browser/search, project filesystem, cloud providers, and local
observability services without enabling or requiring any credentials.

## Recommended CLIs

| CLI | Purpose |
|-----|---------|
| `git` | Repository state, history, branches, diffs |
| `gh` | GitHub issues, pull requests, checks, workflows |
| `docker` | Local containers and compose-managed services |
| `uv` | Python environment, dependency, and test execution |
| `curl` | HTTP health checks and API inspection |
| `jq` | JSON inspection from CLI responses |
| `aws`, `gcloud`, `az` | Cloud state when the project uses those providers |
| `opencode`, `claude` | Local agent/runtime diagnostics |

Run:

```bash
make toolbelt-doctor
```

The doctor reports installed/missing CLIs and probes optional local services only
when their environment variables are set.

## Tool Choice Rule

Use the lightest tool that can retrieve the fact:

1. Use `make` targets and project CLIs for reproducible repository operations.
2. Use MCP when structured context is better than raw shell output, especially
   current docs or repository metadata.
3. Use direct CLIs for external systems that already have authenticated local
   tooling, such as `gh`, `docker`, `aws`, `gcloud`, or `az`.
4. Ask the user only when the information cannot be retrieved with available
   tools, requires a product decision, or needs credentials they have not
   configured.

## Common Tasks

### Inspect a GitHub Issue or PR

Prefer `gh` when it is installed and authenticated:

```bash
gh issue view 123 --comments
gh pr view 123 --json title,body,headRefName,baseRefName,reviewDecision,statusCheckRollup
gh pr diff 123
```

If a GitHub MCP server is configured, use it for structured issue, PR, review, or
thread metadata before falling back to CLI text output.

### Check Local Services

Start with the repo doctor:

```bash
make toolbelt-doctor
```

For container-managed services, inspect Docker directly:

```bash
docker ps
docker compose ps
docker compose logs --tail=100
```

### Inspect Dependency Docs

Use `context7` first for current library documentation. If the dependency is
project-local, inspect `pyproject.toml`, `uv.lock`, and relevant source files
before asking the user.

Useful local commands:

```bash
uv tree
uv run python -m pip show <package>
```

### Check Cloud or Deployment State

Use whichever cloud CLI the project has configured:

```bash
aws sts get-caller-identity
gcloud config list
az account show
```

Do not add credentials to the repository. If authentication is missing, report
the exact missing local login/config step instead of inventing state.

### Query AI Gateway, Langfuse, MLflow, Ollama, or LM Studio

The doctor checks these only when configured:

| Env var | Service |
|---------|---------|
| `GATEWAY_BASE_URL` | LiteLLM or compatible AI gateway |
| `LANGFUSE_HOST` | Langfuse |
| `MLFLOW_TRACKING_URI` | MLflow |
| `OLLAMA_BASE_URL` | Ollama |
| `LMSTUDIO_BASE_URL` | LM Studio |

Direct checks:

```bash
curl "$GATEWAY_BASE_URL/models"
curl "$LANGFUSE_HOST/api/public/health"
curl "$MLFLOW_TRACKING_URI/health"
curl "$OLLAMA_BASE_URL/models"
curl "$LMSTUDIO_BASE_URL/models"
```

Use `GATEWAY_TOKEN` from the local environment when the gateway requires bearer
auth. Never write tokens into docs, examples, shell history snippets, or commits.
