"""Load and validate the declarative tool registry (``adapters/registry.toml``)."""

from __future__ import annotations

import tomllib
from pathlib import Path

from ml_python_base.skills_sync.errors import RegistryError
from ml_python_base.skills_sync.models import (
    VALID_LINK_STRATEGIES,
    Alias,
    CatalogSpec,
    Governance,
    Intent,
    Policy,
    Registry,
    TemplateSyncPolicy,
    ToolSpec,
)

DEFAULT_REGISTRY_PATH = Path("adapters/registry.toml")


def load_registry(path: Path = DEFAULT_REGISTRY_PATH) -> Registry:
    """Parse, validate, and return the registry from ``path``."""
    if not path.is_file():
        raise RegistryError(f"Registry not found: {path}")

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:  # pragma: no cover - defensive
        raise RegistryError(f"Invalid TOML in {path}: {exc}") from exc

    governance = _parse_governance(raw.get("governance", {}))
    template_sync = _parse_template_sync(raw.get("template_sync", {}))
    tools = _parse_tools(raw.get("tool", []))
    if not tools:
        raise RegistryError("Registry declares no [[tool]] entries.")
    catalog = _parse_catalog(raw)

    return Registry(
        schema_version=int(raw.get("schema_version", 1)),
        governance=governance,
        tools=tuple(tools),
        template_sync=template_sync,
        catalog=catalog,
    )


def load_external_skill_provenance(
    path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, dict[str, str]]:
    """Return ``{skill_name: {"upstream": ..., "license": ...}}`` from the registry.

    Redistribution metadata for vendored skills. Missing or unreadable registry
    yields an empty map, which renders as "UNKNOWN" in the lock rather than
    failing the sync — an unknown origin must be visible, not fatal.
    """
    if not path.is_file():
        return {}
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return {}

    block = raw.get("external_skill", {})
    if not isinstance(block, dict):
        return {}
    return {
        str(name): {
            "upstream": str(entry.get("upstream", "UNKNOWN")),
            "license": str(entry.get("license", "UNKNOWN")),
        }
        for name, entry in block.items()
        if isinstance(entry, dict)
    }


def _parse_governance(block: dict) -> Governance:
    files = tuple(block.get("files", ()))
    return Governance(
        files=files,
        automation=str(block.get("automation", "")),
        orchestration=str(block.get("orchestration", "")),
    )


def _parse_template_sync(block: dict) -> TemplateSyncPolicy:
    protocol = int(block.get("protocol", 0))
    if protocol < 0:
        raise RegistryError("template_sync protocol must be zero or greater.")

    governance_paths = _parse_sync_paths(block, "governance_paths")
    platform_paths = _parse_sync_paths(block, "platform_paths")
    overlap = sorted(set(governance_paths) & set(platform_paths))
    if overlap:
        raise RegistryError(
            "template_sync governance/platform paths overlap: " + ", ".join(overlap)
        )
    return TemplateSyncPolicy(
        protocol=protocol,
        governance_paths=governance_paths,
        platform_paths=platform_paths,
    )


def _parse_sync_paths(block: dict, key: str) -> tuple[str, ...]:
    raw_paths = block.get(key, ())
    if not isinstance(raw_paths, list | tuple):
        raise RegistryError(f"template_sync {key} must be a list of paths.")
    paths = tuple(str(path).strip().rstrip("/") for path in raw_paths)
    if any(not path for path in paths):
        raise RegistryError(f"template_sync {key} contains an empty path.")
    if len(paths) != len(set(paths)):
        raise RegistryError(f"template_sync {key} contains duplicate paths.")
    return paths


def _parse_tools(entries: list[dict]) -> list[ToolSpec]:
    tools: list[ToolSpec] = []
    seen: set[str] = set()
    for entry in entries:
        tool = _parse_tool(entry)
        if tool.id in seen:
            raise RegistryError(f"Duplicate tool id in registry: {tool.id}")
        seen.add(tool.id)
        tools.append(tool)
    return tools


def _parse_tool(entry: dict) -> ToolSpec:
    tool_id = entry.get("id")
    if not tool_id:
        raise RegistryError(f"A [[tool]] entry is missing 'id': {entry!r}")

    strategy = entry.get("link_strategy", "none")
    if strategy not in VALID_LINK_STRATEGIES:
        raise RegistryError(
            f"Tool '{tool_id}' has invalid link_strategy '{strategy}'. "
            f"Expected one of {sorted(VALID_LINK_STRATEGIES)}."
        )

    needs_manifest = bool(entry.get("needs_manifest", False))
    manifest_path = entry.get("manifest_path")
    if needs_manifest and not manifest_path:
        raise RegistryError(
            f"Tool '{tool_id}' sets needs_manifest but no manifest_path."
        )

    return ToolSpec(
        id=str(tool_id),
        display_name=str(entry.get("display_name", tool_id)),
        link_strategy=strategy,
        native_skills_dir=str(entry.get("native_skills_dir", "")),
        needs_manifest=needs_manifest,
        manifest_path=manifest_path,
        adapter_file=entry.get("adapter_file"),
        adapter_template=entry.get("adapter_template"),
        reference_prefix=str(entry.get("reference_prefix", "")),
        adapter_frontmatter=entry.get("adapter_frontmatter"),
        native_agents_dir=str(entry.get("native_agents_dir", "")),
        agent_format=str(entry.get("agent_format", "")),
    )


# --- Catalog blocks -----------------------------------------------------------


def _parse_catalog(raw: dict) -> CatalogSpec:
    block = raw.get("catalog", {})
    if not isinstance(block, dict):
        raise RegistryError("[catalog] must be a table.")
    return CatalogSpec(
        families=_str_tuple(block.get("families", ()), "[catalog].families"),
        profiles=_str_tuple(block.get("profiles", ()), "[catalog].profiles"),
        output=str(block.get("output", "")).strip(),
        routing_rules=_str_tuple(
            block.get("routing_rules", ()), "[catalog].routing_rules"
        ),
        small_model_note=" ".join(str(block.get("small_model_note", "")).split()),
        overlays=_parse_named_tables(raw.get("skill", {}), "skill"),
        aliases=_parse_aliases(raw.get("alias", {})),
        policies=_parse_policies(raw.get("policy", {})),
        intents=_parse_intents(raw.get("intent", [])),
    )


def _str_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise RegistryError(f"{label} must be a list of strings.")
    items = tuple(str(item).strip() for item in value)
    if any(not item for item in items):
        raise RegistryError(f"{label} contains an empty entry.")
    if len(items) != len(set(items)):
        raise RegistryError(f"{label} contains duplicates.")
    return items


def _parse_named_tables(block: object, label: str) -> dict[str, dict]:
    if not isinstance(block, dict):
        raise RegistryError(f"[{label}.*] entries must be tables.")
    tables: dict[str, dict] = {}
    for name, entry in block.items():
        if not isinstance(entry, dict):
            raise RegistryError(f"[{label}.{name}] must be a table.")
        tables[str(name)] = dict(entry)
    return tables


def _parse_aliases(block: object) -> tuple[Alias, ...]:
    aliases: list[Alias] = []
    for name, entry in _parse_named_tables(block, "alias").items():
        replacement = str(entry.get("replacement", "")).strip()
        if not replacement:
            raise RegistryError(f"[alias.{name}] is missing 'replacement'.")
        aliases.append(
            Alias(name=name, replacement=replacement, note=str(entry.get("note", "")))
        )
    return tuple(sorted(aliases, key=lambda a: a.name))


def _parse_policies(block: object) -> tuple[Policy, ...]:
    policies: list[Policy] = []
    for policy_id, entry in _parse_named_tables(block, "policy").items():
        summary = str(entry.get("summary", "")).strip()
        if not summary:
            raise RegistryError(f"[policy.{policy_id}] is missing 'summary'.")
        policies.append(
            Policy(
                id=policy_id,
                title=str(entry.get("title", policy_id)).strip(),
                summary=" ".join(summary.split()),
                applies_to=_str_tuple(
                    entry.get("applies_to", ()), f"[policy.{policy_id}].applies_to"
                ),
                doc=str(entry.get("doc", "")).strip(),
            )
        )
    return tuple(sorted(policies, key=lambda p: p.id))


def _parse_intents(entries: object) -> tuple[Intent, ...]:
    if not isinstance(entries, list):
        raise RegistryError("[[intent]] must be an array of tables.")
    intents: list[Intent] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RegistryError("[[intent]] entries must be tables.")
        want = str(entry.get("want", "")).strip()
        skill = str(entry.get("skill", "")).strip()
        if not want or not skill:
            raise RegistryError("[[intent]] entries need 'want' and 'skill'.")
        intents.append(Intent(want=want, skill=skill, note=str(entry.get("note", ""))))
    return tuple(intents)
