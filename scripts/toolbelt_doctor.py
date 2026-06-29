#!/usr/bin/env python3
"""Inspect the local Claude toolbelt: CLIs and optional service endpoints."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from urllib import error, parse, request

HTTP_TIMEOUT_SECONDS = 3.0

CORE_TOOLS = frozenset({"git", "uv", "curl"})
CLI_TOOLS: tuple[str, ...] = (
    "git",
    "gh",
    "docker",
    "uv",
    "curl",
    "jq",
    "aws",
    "gcloud",
    "az",
    "opencode",
    "claude",
)


@dataclass(frozen=True)
class ServiceCheck:
    """Optional local service endpoint exposed through an environment variable."""

    env_var: str
    health_path: str
    note: str


@dataclass(frozen=True)
class Row:
    """One printable diagnostic result."""

    name: str
    kind: str
    status: str
    source: str
    note: str


SERVICE_CHECKS: tuple[ServiceCheck, ...] = (
    ServiceCheck("GATEWAY_BASE_URL", "/models", "AI gateway / LiteLLM"),
    ServiceCheck("LANGFUSE_HOST", "/api/public/health", "Langfuse"),
    ServiceCheck("MLFLOW_TRACKING_URI", "/health", "MLflow"),
    ServiceCheck("OLLAMA_BASE_URL", "/models", "Ollama"),
    ServiceCheck("LMSTUDIO_BASE_URL", "/models", "LM Studio"),
)


def _join_url(base_url: str, path: str) -> str:
    """Join a base URL and path while preserving API prefixes such as /v1."""
    trimmed = base_url.rstrip("/")
    if trimmed.endswith(path):
        return trimmed
    return f"{trimmed}{path}"


def check_cli_tools() -> list[Row]:
    """Return diagnostics for expected command-line tools."""
    rows: list[Row] = []
    for tool in CLI_TOOLS:
        path = shutil.which(tool)
        required = "core" if tool in CORE_TOOLS else "optional"
        if path:
            rows.append(Row(tool, "cli", "installed", path, required))
        else:
            rows.append(Row(tool, "cli", "missing", "-", required))
    return rows


def _health_request(url: str) -> request.Request:
    headers = {"User-Agent": "ml-python-base-toolbelt-doctor/1.0"}
    token = os.environ.get("GATEWAY_TOKEN")
    if (
        token
        and parse.urlparse(url).netloc
        == parse.urlparse(os.environ.get("GATEWAY_BASE_URL", "")).netloc
    ):
        headers["Authorization"] = f"Bearer {token}"
    return request.Request(url, headers=headers)


def check_service(service: ServiceCheck) -> Row:
    """Return a diagnostic row for one optional service."""
    base_url = os.environ.get(service.env_var, "").strip()
    if not base_url:
        return Row(
            service.env_var,
            "service",
            "not configured",
            service.env_var,
            service.note,
        )

    url = _join_url(base_url, service.health_path)
    try:
        # Env-configured local endpoints are intentionally probed by this doctor.
        with request.urlopen(  # nosec B310
            _health_request(url), timeout=HTTP_TIMEOUT_SECONDS
        ) as response:
            status = getattr(response, "status", 200)
            response.read(64)
    except (OSError, error.URLError, error.HTTPError, TimeoutError) as exc:
        return Row(service.env_var, "service", "unreachable", url, str(exc))

    if 200 <= int(status) < 400:
        return Row(service.env_var, "service", "reachable", url, service.note)
    return Row(service.env_var, "service", "unreachable", url, f"HTTP {status}")


def check_services() -> list[Row]:
    """Return diagnostics for optional local services."""
    return [check_service(service) for service in SERVICE_CHECKS]


def print_table(rows: list[Row]) -> None:
    """Print a compact fixed-width table."""
    headers = ("Name", "Kind", "Status", "Source", "Note")
    table = [headers, *[(r.name, r.kind, r.status, r.source, r.note) for r in rows]]
    widths = [max(len(row[index]) for row in table) for index in range(len(headers))]
    template = "  ".join(f"{{:<{width}}}" for width in widths)

    print(template.format(*headers))
    print(template.format(*("-" * width for width in widths)))
    for row in rows:
        print(template.format(row.name, row.kind, row.status, row.source, row.note))


def has_missing_core(rows: list[Row]) -> bool:
    """Return whether any core CLI is missing."""
    return any(
        row.kind == "cli" and row.name in CORE_TOOLS and row.status == "missing"
        for row in rows
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-services",
        action="store_true",
        help="check CLIs only; do not probe configured service URLs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = check_cli_tools()
    if not args.skip_services:
        rows.extend(check_services())

    print_table(rows)
    if has_missing_core(rows):
        print("\nMissing core tools: install git, uv, and curl for this template.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
