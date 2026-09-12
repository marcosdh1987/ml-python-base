"""Dependency-free reader for the YAML frontmatter of ``SKILL.md`` files.

Skills only ever use a small YAML subset — scalars, quoted strings, booleans,
inline lists (``[a, b]``) and block lists (``- item``). Parsing that subset here
keeps the engine free of a YAML dependency while letting skills declare catalog
metadata (family, visibility, triggers, ...) next to their trigger description.
"""

from __future__ import annotations

from typing import Any

FENCE = "---"


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(frontmatter, body)``. A file without a fence yields ``({}, text)``."""
    if not text.startswith(FENCE):
        return {}, text
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == FENCE), None)
    if end is None:
        return {}, text
    return parse_block(lines[1:end]), "\n".join(lines[end + 1 :])


def parse_frontmatter(text: str) -> dict[str, Any]:
    """The frontmatter mapping alone."""
    return split_frontmatter(text)[0]


def parse_block(lines: list[str]) -> dict[str, Any]:
    """Parse the lines between the fences into a mapping."""
    data: dict[str, Any] = {}
    key: str | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and (raw[:1].isspace() or key is not None):
            if key is None:
                continue
            existing = data.get(key)
            if not isinstance(existing, list):
                existing = []
                data[key] = existing
            existing.append(_scalar(stripped[2:]))
            continue
        if raw[:1].isspace() or ":" not in raw:
            continue
        name, _, value = raw.partition(":")
        key = name.strip()
        data[key] = _value(value.strip())
    return data


def _value(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_scalar(part) for part in _split_list(inner)] if inner else []
    return _scalar(value)


def _scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    return value


def _split_list(inner: str) -> list[str]:
    """Split an inline list on commas that are not inside quotes."""
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in inner:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
            current.append(char)
        elif char == ",":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return [part for part in (p.strip() for p in parts) if part]


def as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "1"):
            return True
        if lowered in ("false", "no", "0"):
            return False
    return default


def as_str_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, list | tuple):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value),)
