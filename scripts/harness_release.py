#!/usr/bin/env python3
"""Traceable template release contract — guarded preflight and publish tooling.

This script is read-only by default: it validates that a release is coherent,
classifies governance vs. platform changes, recommends a SemVer bump, generates
the release manifest asset, and prints the exact commands. Git mutation happens
ONLY inside two guarded subcommands — `release-pr` and `publish` — each of which
requires its full guard set to pass and then an explicit interactive confirmation
(or `--yes`). `prepare` performs the mechanical Step-2 file edits (pyproject.toml
and CHANGELOG.md) locally, exactly like `make fix` mutates the tree locally.

Subcommands:
    change-summary    [--base-ref REF]      Classify changes and recommend a bump.
    platform-summary  [--base-ref REF]      Report platform changes + migration need.
    prepare           [--version X.Y.Z]     Step 2: write the version into
                                            pyproject.toml + scaffold the CHANGELOG
                                            section (file-mutating; git untouched).
    release-pr        [--version X.Y.Z]     Guarded: branch + commit the bump +
                                            push + open the release PR.
    release-check     [--version X.Y.Z]     Read-only release preflight.
    publish           [--version X.Y.Z]     Guarded: preflight, then tag + push +
                                            GitHub Release + manifest + upload.
    release-manifest  --version X.Y.Z       Generate the release asset after tagging.
    release           [--version X.Y.Z]     Preflight + print manual publish steps
                                            (the manual fallback to `publish`).

VERSION defaults to the version in pyproject.toml; BASE_REF defaults to the most
recent tag. Run via `make release-pr` / `make publish-release` etc. All subprocess
calls pass argument arrays (never a shell string). Governance and platform paths
come from adapters/registry.toml [template_sync] — a closed allowlist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "adapters" / "registry.toml"
SCHEMA_PATH = REPO_ROOT / "schemas" / "harness-release-v1.schema.json"
REPOSITORY = "marcosdh1987/ml-python-base"

# Exit codes mirror the harness lifecycle contract (plan §9.1).
EXIT_OK = 0
EXIT_INVALID = 2  # invalid arguments or malformed manifest
EXIT_PRECONDITION = 3  # failed precondition or dirty tree
EXIT_INCOMPAT = 4  # sync protocol / platform incompatibility
EXIT_DRIFT = 5  # conflict, drift, or forbidden-path change
EXIT_MISSING = 7  # missing tag, asset, external tool, network, or auth

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# The version bump itself always touches exactly these platform paths; a platform
# delta that is a subset of this pair is the release, not a platform change.
VERSION_BUMP_PATHS = frozenset({"pyproject.toml", "uv.lock"})


class ReleaseError(Exception):
    """Raised on invalid input; carries the process exit code to surface."""

    def __init__(self, message: str, exit_code: int = EXIT_INVALID) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class Problem:
    """A single preflight finding. `error` severity blocks the release."""

    code: str
    message: str
    exit_code: int
    severity: str = "error"


@dataclass(frozen=True)
class Provenance:
    proposals: tuple[str, ...] = ()
    source_issues: tuple[str, ...] = ()
    source_pull_requests: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return not (self.proposals or self.source_issues or self.source_pull_requests)


@dataclass(frozen=True)
class Classification:
    governance: tuple[str, ...] = ()
    platform: tuple[str, ...] = ()
    other: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# Subprocess helper (argument arrays only — never a shell string)
# --------------------------------------------------------------------------- #


def run(
    cmd: list[str],
    root: Path | None = None,
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=root or REPO_ROOT,
        text=True,
        check=check,
        capture_output=capture,
    )


# --------------------------------------------------------------------------- #
# SemVer
# --------------------------------------------------------------------------- #


def is_valid_semver(version: str) -> bool:
    return bool(SEMVER_RE.match(version))


def parse_semver(version: str) -> tuple[int, int, int]:
    if not is_valid_semver(version):
        raise ReleaseError(
            f"Invalid SemVer '{version}'. Expected MAJOR.MINOR.PATCH (e.g. 0.2.0).",
            EXIT_INVALID,
        )
    major, minor, patch = (int(x) for x in version.split("."))
    return major, minor, patch


# --------------------------------------------------------------------------- #
# Repository readers
# --------------------------------------------------------------------------- #


def read_pyproject_version(root: Path) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data.get("project", {}).get("version", ""))


def changelog_has_section(root: Path, version: str) -> bool:
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    return bool(re.search(rf"^## \[{re.escape(version)}\]", text, flags=re.M))


def tag_exists(root: Path, version: str, runner=run) -> bool:
    tag = f"v{version}"
    out = runner(["git", "tag", "--list", tag], root, capture=True).stdout.strip()
    return bool(out)


def working_tree_clean(root: Path, runner=run) -> bool:
    out = runner(["git", "status", "--porcelain"], root, capture=True).stdout.strip()
    return not out


def dirty_files(root: Path, runner=run) -> list[str]:
    """Paths with any uncommitted change (staged, unstaged, or untracked)."""
    out = runner(["git", "status", "--porcelain"], root, capture=True).stdout
    files: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        # Renames are reported as 'old -> new'; the new path is what matters.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def current_branch(root: Path, runner=run) -> str:
    return runner(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], root, capture=True
    ).stdout.strip()


def extract_changelog_section(root: Path, version: str) -> str:
    """Return the body of the '## [version]' CHANGELOG section (heading excluded)."""
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        rf"^## \[{re.escape(version)}\]\n(.*?)(?=^## \[|\Z)",
        text,
        flags=re.M | re.S,
    )
    if match is None:
        raise ReleaseError(
            f"CHANGELOG.md has no '## [{version}]' section.", EXIT_PRECONDITION
        )
    return match.group(1).strip() + "\n"


def load_sync_policy(root: Path) -> tuple[list[str], list[str], int]:
    """Return (governance_paths, platform_paths, protocol) from the registry."""
    data = tomllib.loads((root / "adapters/registry.toml").read_text(encoding="utf-8"))
    section = data.get("template_sync", {})
    governance = list(section.get("governance_paths", []))
    platform = list(section.get("platform_paths", []))
    protocol = int(section.get("protocol", 0))
    return governance, platform, protocol


def changed_paths(root: Path, base_ref: str, runner=run) -> list[tuple[str, str]]:
    """Return (status, path) tuples for base_ref..HEAD via name-status."""
    out = runner(
        ["git", "diff", "--name-status", f"{base_ref}..HEAD"],
        root,
        capture=True,
    ).stdout
    entries: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0]  # R100 → R, M → M, etc.
        path = parts[-1]  # renames put the new path last
        entries.append((status, path))
    return entries


# --------------------------------------------------------------------------- #
# Classification and SemVer recommendation
# --------------------------------------------------------------------------- #


def _matches(path: str, prefixes: list[str]) -> bool:
    return any(path == p or path.startswith(p + "/") for p in prefixes)


def classify_paths(
    entries: list[tuple[str, str]],
    governance: list[str],
    platform: list[str],
) -> Classification:
    gov: list[str] = []
    plat: list[str] = []
    other: list[str] = []
    removed: list[str] = []
    for status, path in entries:
        if status == "D":
            removed.append(path)
        if _matches(path, governance):
            gov.append(path)
        elif _matches(path, platform):
            plat.append(path)
        else:
            other.append(path)
    return Classification(
        governance=tuple(gov),
        platform=tuple(plat),
        other=tuple(other),
        removed=tuple(removed),
    )


def recommend_bump(classification: Classification) -> str:
    if classification.removed or classification.platform:
        return "major"
    if classification.governance:
        return "minor"
    return "patch"


def bump_version(version: str, bump: str) -> str:
    """Apply a SemVer bump to a MAJOR.MINOR.PATCH version string."""
    major, minor, patch = parse_semver(version)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


# --------------------------------------------------------------------------- #
# Release preparation (Step 2) — the only file-mutating subcommand.
# Writes the new version into pyproject.toml and scaffolds the CHANGELOG
# section. Git stays untouched: branching, committing, and the PR are manual.
# --------------------------------------------------------------------------- #


def latest_tag(root: Path, runner=run) -> str | None:
    """Return the most recent reachable tag (e.g. 'v0.3.0'), or None."""
    out = runner(
        ["git", "describe", "--tags", "--abbrev=0"], root, check=False, capture=True
    ).stdout.strip()
    return out or None


def resolve_version(root: Path, version: str | None) -> str:
    """Explicit --version, else the version pyproject.toml already carries."""
    if version:
        return version
    resolved = read_pyproject_version(root)
    if not resolved:
        raise ReleaseError(
            "No --version given and pyproject.toml carries no [project] version.",
            EXIT_PRECONDITION,
        )
    print(f"👉 VERSION not given — using pyproject.toml: {resolved}")
    return resolved


def resolve_base_ref(root: Path, base_ref: str | None, runner=run) -> str | None:
    """Explicit --base-ref, else the latest reachable tag (None on a tagless repo).

    Printing the resolution matters: without a base ref the platform/provenance
    classification is skipped entirely, and that must never happen silently.
    """
    if base_ref:
        return base_ref
    resolved = latest_tag(root, runner)
    if resolved:
        print(f"👉 BASE_REF not given — using latest tag: {resolved}")
    else:
        print("⚠️  BASE_REF not given and no tag exists — classification is skipped.")
    return resolved


def pending_release(root: Path, runner=run) -> str | None:
    """Version reconciled in pyproject.toml but never tagged, or None.

    pyproject 0.5.0 with latest tag v0.4.0 means 0.5.0 was prepared (maybe even
    merged) but never published. Deriving the *next* bump from that state silently
    skips a release — callers must surface or refuse it.
    """
    current = read_pyproject_version(root)
    tag = latest_tag(root, runner)
    if not current or not is_valid_semver(current):
        return None
    if tag_exists(root, current, runner):
        return None
    if tag is None:
        return current
    tag_version = tag.lstrip("v")
    if not is_valid_semver(tag_version):
        return current
    return current if parse_semver(current) > parse_semver(tag_version) else None


def collect_commit_subjects(root: Path, base_ref: str, runner=run) -> list[str]:
    """Subject lines of non-merge commits in base_ref..HEAD, oldest first."""
    out = runner(
        ["git", "log", "--reverse", "--no-merges", "--format=%s", f"{base_ref}..HEAD"],
        root,
        check=False,
        capture=True,
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def update_pyproject_version(root: Path, new_version: str) -> None:
    """Rewrite the [project] version line in pyproject.toml."""
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    current = read_pyproject_version(root)
    old_line = f'version = "{current}"'
    if old_line not in text:
        raise ReleaseError(
            f"Could not find '{old_line}' in pyproject.toml.", EXIT_PRECONDITION
        )
    path.write_text(
        text.replace(old_line, f'version = "{new_version}"', 1), encoding="utf-8"
    )


def insert_changelog_section(root: Path, version: str, bullets: list[str]) -> None:
    """Insert a '## [version]' section above the first existing section."""
    path = root / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    if changelog_has_section(root, version):
        raise ReleaseError(
            f"CHANGELOG.md already has a '## [{version}]' section.", EXIT_PRECONDITION
        )
    lines = bullets or ["TODO: describe the changes in this release."]
    body = "\n".join(f"- {line}" for line in lines)
    section = f"## [{version}]\n\n### Changed\n{body}\n\n"
    match = re.search(r"^## \[", text, flags=re.M)
    if match is None:
        # First release: append the section at the end of the intro.
        path.write_text(text.rstrip() + "\n\n" + section, encoding="utf-8")
        return
    idx = match.start()
    path.write_text(text[:idx] + section + text[idx:], encoding="utf-8")


def prepare_release(
    root: Path, version: str | None, base_ref: str | None, runner=run
) -> str:
    """Validate, resolve the target version, and mutate the two files.

    Returns the resolved version. Raises ReleaseError before any mutation if a
    precondition fails — the two files are only written together.
    """
    current = read_pyproject_version(root)
    base = base_ref or latest_tag(root, runner)

    if version is None:
        pending = pending_release(root, runner)
        if pending is not None:
            raise ReleaseError(
                f"Release {pending} is reconciled in pyproject.toml but tag "
                f"'v{pending}' does not exist — publish it first "
                "(make publish-release), or pass VERSION=X.Y.Z explicitly to "
                "skip over it.",
                EXIT_PRECONDITION,
            )
        if base is None:
            raise ReleaseError(
                "No VERSION given and no tag found to derive one from. "
                "Pass VERSION=X.Y.Z explicitly.",
                EXIT_PRECONDITION,
            )
        governance, platform, _ = load_sync_policy(root)
        classification = classify_paths(
            changed_paths(root, base, runner), governance, platform
        )
        version = bump_version(current, recommend_bump(classification))

    if parse_semver(version) <= parse_semver(current):
        raise ReleaseError(
            f"Requested version '{version}' is not above the current "
            f"pyproject version '{current}'.",
            EXIT_PRECONDITION,
        )
    if tag_exists(root, version, runner):
        raise ReleaseError(
            f"Tag 'v{version}' already exists; a published tag is never moved.",
            EXIT_PRECONDITION,
        )
    if changelog_has_section(root, version):
        raise ReleaseError(
            f"CHANGELOG.md already has a '## [{version}]' section.", EXIT_PRECONDITION
        )

    bullets = collect_commit_subjects(root, base, runner) if base else []
    update_pyproject_version(root, version)
    insert_changelog_section(root, version, bullets)
    return version


# --------------------------------------------------------------------------- #
# Release preflight
# --------------------------------------------------------------------------- #


def check_release(
    root: Path,
    version: str,
    *,
    base_ref: str | None = None,
    provenance: Provenance | None = None,
    require_provenance: bool = False,
    allow_platform: bool = False,
    check_git: bool = True,
    runner=run,
) -> list[Problem]:
    problems: list[Problem] = []

    if not is_valid_semver(version):
        problems.append(
            Problem(
                "invalid_semver",
                f"Invalid SemVer '{version}'. Expected MAJOR.MINOR.PATCH.",
                EXIT_INVALID,
            )
        )
        return problems  # nothing else is meaningful

    py_version = read_pyproject_version(root)
    if py_version != version:
        problems.append(
            Problem(
                "version_mismatch",
                f"pyproject.toml is '{py_version}', requested release is '{version}'.",
                EXIT_PRECONDITION,
            )
        )

    if not changelog_has_section(root, version):
        problems.append(
            Problem(
                "changelog_missing",
                f"CHANGELOG.md has no '## [{version}]' section.",
                EXIT_PRECONDITION,
            )
        )

    if tag_exists(root, version, runner):
        problems.append(
            Problem(
                "tag_exists",
                f"Tag 'v{version}' already exists; a published tag is never moved.",
                EXIT_PRECONDITION,
            )
        )

    if check_git and not working_tree_clean(root, runner):
        problems.append(
            Problem(
                "dirty_tree",
                "Working tree is not clean; commit or stash before releasing.",
                EXIT_PRECONDITION,
            )
        )

    if base_ref:
        governance, platform, _ = load_sync_policy(root)
        classification = classify_paths(
            changed_paths(root, base_ref, runner), governance, platform
        )
        if classification.platform and not allow_platform:
            # Every release necessarily edits pyproject.toml + uv.lock (the version
            # bump itself). When the platform delta is exactly that pair, the manual
            # verification standards.md used to prescribe is automated here instead
            # of demanding --allow-platform every single time.
            if set(classification.platform) <= VERSION_BUMP_PATHS:
                print(
                    "👉 Platform delta is exactly the version bump "
                    f"({', '.join(sorted(classification.platform))}) — auto-allowed."
                )
            else:
                problems.append(
                    Problem(
                        "platform_change",
                        "Release changes platform paths "
                        f"({', '.join(classification.platform)}); platform changes "
                        "need a separate reviewed PR/release "
                        "(pass --allow-platform to override).",
                        EXIT_INCOMPAT,
                    )
                )
        missing_provenance = provenance is None or provenance.is_empty()
        if require_provenance and classification.governance and missing_provenance:
            problems.append(
                Problem(
                    "provenance_missing",
                    "Governance changed but no proposal/issue/PR provenance was "
                    "supplied (--proposal / --issue / --pr).",
                    EXIT_PRECONDITION,
                )
            )

    return problems


# --------------------------------------------------------------------------- #
# Release manifest
# --------------------------------------------------------------------------- #


def build_release_manifest(
    *,
    repository: str,
    version: str,
    commit: str,
    published_at: str,
    sync_protocol: int,
    min_consumer_protocol: int,
    breaking: bool,
    migration_document: str | None,
    governance_paths: list[str],
    platform_changed: bool,
    platform_paths: list[str],
    proposals: list[str],
    source_issues: list[str],
    source_pull_requests: list[str],
    governance_tree_sha256: str,
    skills_lock_sha256: str,
    registry_sha256: str,
) -> dict:
    return {
        "schema_version": 1,
        "release": {
            "repository": repository,
            "version": version,
            "ref": f"v{version}",
            "commit": commit,
            "published_at": published_at,
        },
        "compatibility": {
            "sync_protocol": sync_protocol,
            "minimum_consumer_protocol": min_consumer_protocol,
            "breaking": breaking,
            "migration_document": migration_document,
        },
        "channels": {
            "governance": {"paths": list(governance_paths)},
            "platform": {"changed": platform_changed, "paths": list(platform_paths)},
        },
        "provenance": {
            "proposals": list(proposals),
            "source_issues": list(source_issues),
            "source_pull_requests": list(source_pull_requests),
        },
        "artifacts": {
            "governance_tree_sha256": governance_tree_sha256,
            "skills_lock_sha256": skills_lock_sha256,
            "registry_sha256": registry_sha256,
        },
    }


def hash_tree_at_ref(root: Path, paths: list[str], ref: str, runner=run) -> str:
    """SHA-256 over the sorted (path, blob) pairs of every file under `paths`."""
    files: set[str] = set()
    for base in paths:
        out = runner(
            ["git", "ls-tree", "-r", "--name-only", ref, "--", base],
            root,
            capture=True,
        ).stdout
        files.update(f for f in out.splitlines() if f.strip())
    digest = hashlib.sha256()
    for f in sorted(files):
        blob = runner(["git", "show", f"{ref}:{f}"], root, capture=True).stdout
        digest.update(f.encode("utf-8"))
        digest.update(b"\0")
        digest.update(blob.encode("utf-8"))
    return "sha256:" + digest.hexdigest()


def hash_file_at_ref(root: Path, path: str, ref: str, runner=run) -> str:
    blob = runner(["git", "show", f"{ref}:{path}"], root, capture=True).stdout
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Minimal JSON-Schema validator (no third-party dependency)
# --------------------------------------------------------------------------- #

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(instance: object, expected: str) -> bool:
    if expected == "integer":
        # bool is a subclass of int but is not an integer for our contract.
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    return isinstance(instance, _TYPE_MAP[expected])


def validate_manifest(instance: object, schema: dict, path: str = "$") -> list[str]:
    """Validate against the subset of JSON Schema this contract uses.

    Supports: type (scalar or list), const, required, properties, items, enum,
    pattern, minimum, minLength. Returns a list of human-readable error strings.
    """
    errors: list[str] = []

    expected = schema.get("type")
    if expected is not None:
        options = [expected] if isinstance(expected, str) else expected
        if not any(_type_ok(instance, opt) for opt in options):
            errors.append(
                f"{path}: expected type {expected}, got {type(instance).__name__}"
            )
            return errors

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in enum {schema['enum']}")

    if isinstance(instance, str):
        pattern = schema.get("pattern")
        if pattern and not re.match(pattern, instance):
            errors.append(f"{path}: {instance!r} does not match pattern {pattern}")
        min_length = schema.get("minLength")
        if min_length is not None and len(instance) < min_length:
            errors.append(f"{path}: shorter than minLength {min_length}")

    if isinstance(instance, int) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        if minimum is not None and instance < minimum:
            errors.append(f"{path}: {instance} below minimum {minimum}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property '{key}'")
        for key, subschema in schema.get("properties", {}).items():
            if key in instance:
                errors.extend(
                    validate_manifest(instance[key], subschema, f"{path}.{key}")
                )

    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors.extend(validate_manifest(item, schema["items"], f"{path}[{i}]"))

    return errors


# --------------------------------------------------------------------------- #
# Deterministic YAML serializer for the manifest (no third-party dependency)
# --------------------------------------------------------------------------- #


def _scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _emit_mapping(mapping: dict, indent: int) -> list[str]:
    pad = " " * indent
    lines: list[str] = []
    for key, value in mapping.items():
        if isinstance(value, dict):
            if value:
                lines.append(f"{pad}{key}:")
                lines.extend(_emit_mapping(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {{}}")
        elif isinstance(value, list):
            if value:
                lines.append(f"{pad}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        sub = _emit_mapping(item, indent + 4)
                        lines.append(f"{pad}  -")
                        lines.extend(sub)
                    else:
                        lines.append(f"{pad}  - {_scalar(item)}")
            else:
                lines.append(f"{pad}{key}: []")
        else:
            lines.append(f"{pad}{key}: {_scalar(value)}")
    return lines


def serialize_yaml(data: dict, indent: int = 0) -> str:
    return "\n".join(_emit_mapping(data, indent)) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _provenance_from_args(args: argparse.Namespace) -> Provenance:
    return Provenance(
        proposals=tuple(args.proposal or ()),
        source_issues=tuple(args.issue or ()),
        source_pull_requests=tuple(args.pr or ()),
    )


def _print_problems(
    problems: list[Problem],
    success: str = "✅ Release preflight passed (read-only).",
) -> int:
    errors = [p for p in problems if p.severity == "error"]
    for p in problems:
        icon = "❌" if p.severity == "error" else "⚠️ "
        print(f"{icon} [{p.code}] {p.message}")
    if errors:
        return errors[0].exit_code
    print(success)
    return EXIT_OK


def _run_gates() -> list[Problem]:
    problems: list[Problem] = []
    for target in ("check", "check-sync"):
        result = run(["make", target], REPO_ROOT, check=False)
        if result.returncode != 0:
            problems.append(
                Problem(
                    "gate_failed",
                    f"`make {target}` failed (exit {result.returncode}).",
                    EXIT_DRIFT if target == "check-sync" else EXIT_PRECONDITION,
                )
            )
    return problems


def cmd_change_summary(args: argparse.Namespace) -> int:
    base_ref = resolve_base_ref(REPO_ROOT, args.base_ref)
    if base_ref is None:
        print("❌ No --base-ref given and no tag exists to compare against.")
        return EXIT_PRECONDITION
    pending = pending_release(REPO_ROOT)
    if pending is not None:
        print(
            f"⚠️  Release {pending} is reconciled in pyproject.toml but tag "
            f"'v{pending}' does not exist — publish it first: make publish-release."
        )
    governance, platform, _ = load_sync_policy(REPO_ROOT)
    classification = classify_paths(
        changed_paths(REPO_ROOT, base_ref), governance, platform
    )
    bump = recommend_bump(classification)
    current = read_pyproject_version(REPO_ROOT)
    next_version = bump_version(current, bump)
    print(f"📊 Change summary since {base_ref}:")
    print(f"   governance: {len(classification.governance)} path(s)")
    print(f"   platform:   {len(classification.platform)} path(s)")
    print(f"   other:      {len(classification.other)} path(s)")
    print(f"   removed:    {len(classification.removed)} path(s)")
    print(
        f"👉 Recommended bump: {bump.upper()}  (current {current} → next {next_version})"
    )
    print(
        f"   Use this version in pyproject.toml, CHANGELOG.md, and the release: {next_version}"
    )
    if classification.platform:
        print("   ⚠️  Platform paths changed — needs a separate reviewed PR/release.")
    return EXIT_OK


def cmd_platform_summary(args: argparse.Namespace) -> int:
    base_ref = resolve_base_ref(REPO_ROOT, args.base_ref)
    if base_ref is None:
        print("❌ No --base-ref given and no tag exists to compare against.")
        return EXIT_PRECONDITION
    governance, platform, _ = load_sync_policy(REPO_ROOT)
    classification = classify_paths(
        changed_paths(REPO_ROOT, base_ref), governance, platform
    )
    if not classification.platform:
        print("✅ No platform-path changes; governance-only release is possible.")
        return EXIT_OK
    print("⚠️  Platform changes detected (require a migration note and MAJOR review):")
    for path in classification.platform:
        print(f"   · {path}")
    return EXIT_OK


def cmd_release_check(args: argparse.Namespace) -> int:
    version = resolve_version(REPO_ROOT, args.version)
    problems = check_release(
        REPO_ROOT,
        version,
        base_ref=resolve_base_ref(REPO_ROOT, args.base_ref),
        provenance=_provenance_from_args(args),
        require_provenance=args.require_provenance,
        allow_platform=args.allow_platform,
        check_git=not args.skip_git,
    )
    if not args.skip_gates and not any(p.code == "invalid_semver" for p in problems):
        problems.extend(_run_gates())
    return _print_problems(problems)


def write_release_manifest(
    root: Path,
    version: str,
    published_at: str,
    *,
    breaking: bool = False,
    migration: str | None = None,
    provenance: Provenance | None = None,
    runner=run,
) -> Path:
    """Build, validate, and write the manifest for an already-existing tag.

    Returns the written path. Raises ReleaseError on any precondition failure.
    """
    prov = provenance or Provenance()
    if not is_valid_semver(version):
        raise ReleaseError(f"Invalid SemVer '{version}'.", EXIT_INVALID)
    ref = f"v{version}"
    if not tag_exists(root, version, runner):
        raise ReleaseError(
            f"Tag '{ref}' does not exist yet. Create the tag before the manifest.",
            EXIT_MISSING,
        )
    commit = runner(["git", "rev-parse", ref], root, capture=True).stdout.strip()
    governance, _platform, protocol = load_sync_policy(root)
    manifest = build_release_manifest(
        repository=REPOSITORY,
        version=version,
        commit=commit,
        published_at=published_at,
        sync_protocol=protocol,
        min_consumer_protocol=protocol,
        breaking=breaking,
        migration_document=migration,
        governance_paths=governance,
        platform_changed=False,
        platform_paths=[],
        proposals=list(prov.proposals),
        source_issues=list(prov.source_issues),
        source_pull_requests=list(prov.source_pull_requests),
        governance_tree_sha256=hash_tree_at_ref(root, governance, ref, runner),
        skills_lock_sha256=hash_file_at_ref(root, "skills-lock.json", ref, runner),
        registry_sha256=hash_file_at_ref(root, "adapters/registry.toml", ref, runner),
    )
    errors = validate_manifest(manifest, load_schema())
    if errors:
        detail = "\n".join(f"   · {e}" for e in errors)
        raise ReleaseError(
            f"Generated manifest failed schema validation:\n{detail}", EXIT_INVALID
        )
    # Written under the git-ignored dist/ so the release asset is never
    # accidentally committed (it carries a self-referential commit SHA).
    dist_dir = root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    out_path = dist_dir / f"harness-release-{ref}.yaml"
    out_path.write_text(serialize_yaml(manifest), encoding="utf-8")
    return out_path


def cmd_release_manifest(args: argparse.Namespace) -> int:
    ref = f"v{args.version}"
    out_path = write_release_manifest(
        REPO_ROOT,
        args.version,
        args.published_at,
        breaking=args.breaking,
        migration=args.migration,
        provenance=_provenance_from_args(args),
    )
    rel = out_path.relative_to(REPO_ROOT)
    print(f"✅ Wrote release manifest: {rel}")
    print(f"   Attach it manually to the GitHub Release for {ref}:")
    print(f"   gh release upload {ref} {rel}")
    return EXIT_OK


def cmd_release(args: argparse.Namespace) -> int:
    version = resolve_version(REPO_ROOT, args.version)
    problems = check_release(
        REPO_ROOT,
        version,
        base_ref=resolve_base_ref(REPO_ROOT, args.base_ref),
        provenance=_provenance_from_args(args),
        require_provenance=args.require_provenance,
        allow_platform=args.allow_platform,
        check_git=True,
    )
    if not args.skip_gates and not any(p.code == "invalid_semver" for p in problems):
        problems.extend(_run_gates())
    code = _print_problems(problems)
    if code != EXIT_OK:
        return code
    ref = f"v{version}"
    print("\n📋 Preflight passed. `make publish-release` runs these for you after a")
    print("   confirmation — or run them MANUALLY:")
    print("   # 1. Create and push the immutable annotated tag")
    print(f'   git tag -a {ref} -m "Template release {ref}"')
    print(f"   git push origin {ref}")
    print("   # 2. Create the GitHub Release")
    print(f'   gh release create {ref} --title {ref} --notes "Template release {ref}"')
    print("   # 3. Generate the release manifest (written to git-ignored dist/)")
    print(
        f"   make harness-release-manifest VERSION={version} "
        "PUBLISHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    )
    print("   # 4. Attach the manifest asset to the Release")
    print(f"   gh release upload {ref} dist/harness-release-{ref}.yaml")
    return EXIT_OK


def _confirm(prompt: str, *, yes: bool) -> bool:
    """Explicit human gate in front of every mutation. --yes bypasses it."""
    if yes:
        print(f"{prompt} — confirmed via --yes.")
        return True
    if not sys.stdin.isatty():
        print("❌ Non-interactive session without --yes; refusing to mutate.")
        return False
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def _print_plan(title: str, labels: list[str]) -> None:
    print(f"\n📋 {title}")
    for i, label in enumerate(labels, 1):
        print(f"   {i}. {label}")


def _execute_steps(steps: list[tuple[str, object]], final_message: str) -> int:
    """Run (label, action) steps in order; stop at the first failure.

    Completed mutations are never rolled back (a pushed tag is immutable);
    instead the operator gets the exact remaining commands to finish by hand.
    """
    for index, (label, action) in enumerate(steps):
        print(f"▶️  {label}")
        try:
            rc = int(action())  # type: ignore[operator]
        except ReleaseError as exc:
            print(f"❌ {exc}")
            rc = exc.exit_code
        if rc != 0:
            print(f"\n❌ Stopped at: {label}")
            if index:
                print("   Already done (NOT rolled back):")
                for done_label, _ in steps[:index]:
                    print(f"   ✓ {done_label}")
            remaining = steps[index + 1 :]
            if remaining:
                print("   Finish manually:")
                for rest_label, _ in remaining:
                    print(f"   · {rest_label}")
            return rc
    print(f"\n🎉 {final_message}")
    return EXIT_OK


def _git_step(argv: list[str]) -> int:
    # Calls the module-global `run` at call time so tests can intercept it.
    return run(argv, REPO_ROOT, check=False).returncode


RELEASE_PR_FILES = ("pyproject.toml", "CHANGELOG.md", "uv.lock")


def cmd_release_pr(args: argparse.Namespace) -> int:
    version = resolve_version(REPO_ROOT, args.version)
    ref = f"v{version}"
    branch = f"release/{ref}"
    problems: list[Problem] = []

    if not is_valid_semver(version):
        print(f"❌ Invalid SemVer '{version}'.")
        return EXIT_INVALID
    if shutil.which("gh") is None:
        problems.append(
            Problem(
                "gh_missing",
                "GitHub CLI 'gh' not found on PATH (brew install gh).",
                EXIT_MISSING,
            )
        )
    if not changelog_has_section(REPO_ROOT, version):
        problems.append(
            Problem(
                "changelog_missing",
                f"CHANGELOG.md has no '## [{version}]' section — run "
                "`make new-version` first.",
                EXIT_PRECONDITION,
            )
        )
    elif "- TODO:" in extract_changelog_section(REPO_ROOT, version):
        problems.append(
            Problem(
                "changelog_todo",
                f"The '## [{version}]' CHANGELOG section still contains the scaffold "
                "TODO bullet — curate the release notes first.",
                EXIT_PRECONDITION,
            )
        )
    if tag_exists(REPO_ROOT, version):
        problems.append(
            Problem(
                "tag_exists",
                f"Tag '{ref}' already exists; a published tag is never moved.",
                EXIT_PRECONDITION,
            )
        )
    dirty = dirty_files(REPO_ROOT)
    if not dirty:
        problems.append(
            Problem(
                "nothing_to_commit",
                "Working tree is clean — nothing to commit. Run `make new-version` "
                "first (or the bump is already committed; open the PR by hand).",
                EXIT_PRECONDITION,
            )
        )
    extra = sorted(set(dirty) - set(RELEASE_PR_FILES))
    if extra:
        problems.append(
            Problem(
                "unexpected_dirty",
                "Refusing to sweep unrelated changes into the release commit: "
                f"{', '.join(extra)}. Commit or stash them first.",
                EXIT_PRECONDITION,
            )
        )
    on_release_branch = current_branch(REPO_ROOT) == branch
    if not on_release_branch:
        exists = run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
            REPO_ROOT,
            check=False,
            capture=True,
        ).returncode
        if exists == 0:
            problems.append(
                Problem(
                    "branch_exists",
                    f"Branch '{branch}' already exists and is not checked out — "
                    "switch to it or delete it first.",
                    EXIT_PRECONDITION,
                )
            )

    code = _print_problems(problems, success=f"✅ release-pr guards passed for {ref}.")
    if code != EXIT_OK:
        return code

    to_add = [f for f in RELEASE_PR_FILES if f in dirty]
    commit_msg = f"chore(release): reconcile version and changelog for {version}"
    pr_body = f"Version bump + changelog for {ref}."
    steps: list[tuple[str, object]] = []
    if not on_release_branch:
        steps.append(
            (
                f"git switch -c {branch}",
                lambda: _git_step(["git", "switch", "-c", branch]),
            )
        )
    steps.extend(
        [
            (
                f"git add {' '.join(to_add)}",
                lambda: _git_step(["git", "add", *to_add]),
            ),
            (
                f'git commit -m "{commit_msg}"',
                lambda: _git_step(["git", "commit", "-m", commit_msg]),
            ),
            (
                f"git push -u origin {branch}",
                lambda: _git_step(["git", "push", "-u", "origin", branch]),
            ),
            (
                f'gh pr create --title "chore(release): {version}" --body "{pr_body}"',
                lambda: _git_step(
                    [
                        "gh",
                        "pr",
                        "create",
                        "--title",
                        f"chore(release): {version}",
                        "--body",
                        pr_body,
                    ]
                ),
            ),
        ]
    )
    _print_plan(f"Release PR plan for {ref}:", [label for label, _ in steps])
    if args.dry_run:
        print("\n👉 Dry run — nothing executed.")
        return EXIT_OK
    if not _confirm(f"Create release PR for {version}?", yes=args.yes):
        print("Aborted; nothing was executed.")
        return EXIT_PRECONDITION
    return _execute_steps(
        steps,
        f"Release PR for {ref} is open. After the merge, on main: make publish-release",
    )


def cmd_publish(args: argparse.Namespace) -> int:
    version = resolve_version(REPO_ROOT, args.version)
    base_ref = resolve_base_ref(REPO_ROOT, args.base_ref)
    ref = f"v{version}"
    problems: list[Problem] = []

    if shutil.which("gh") is None:
        problems.append(
            Problem(
                "gh_missing",
                "GitHub CLI 'gh' not found on PATH (brew install gh).",
                EXIT_MISSING,
            )
        )
    branch = current_branch(REPO_ROOT)
    if branch != "main":
        problems.append(
            Problem(
                "off_main",
                f"publish runs from 'main' (the tag must record a merged commit); "
                f"current branch is '{branch}'.",
                EXIT_PRECONDITION,
            )
        )
    else:
        fetch = run(
            ["git", "fetch", "origin", "main", "--quiet"], REPO_ROOT, check=False
        )
        if fetch.returncode != 0:
            problems.append(
                Problem(
                    "fetch_failed",
                    "Could not fetch origin/main to verify sync — check network/auth.",
                    EXIT_MISSING,
                )
            )
        else:
            local = run(
                ["git", "rev-parse", "HEAD"], REPO_ROOT, check=False, capture=True
            ).stdout.strip()
            remote = run(
                ["git", "rev-parse", "origin/main"],
                REPO_ROOT,
                check=False,
                capture=True,
            ).stdout.strip()
            if not remote or local != remote:
                problems.append(
                    Problem(
                        "out_of_sync",
                        "Local main does not match origin/main — pull (or push) "
                        "before publishing.",
                        EXIT_PRECONDITION,
                    )
                )

    problems.extend(
        check_release(
            REPO_ROOT,
            version,
            base_ref=base_ref,
            provenance=_provenance_from_args(args),
            require_provenance=args.require_provenance,
            allow_platform=args.allow_platform,
            check_git=True,
        )
    )
    if not args.skip_gates and not any(p.code == "invalid_semver" for p in problems):
        problems.extend(_run_gates())
    code = _print_problems(problems)
    if code != EXIT_OK:
        return code

    notes_rel = f"dist/release-notes-{ref}.md"
    manifest_rel = f"dist/harness-release-{ref}.yaml"
    published_at = (
        datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def _write_notes() -> int:
        notes = extract_changelog_section(REPO_ROOT, version)
        dist_dir = REPO_ROOT / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        (dist_dir / f"release-notes-{ref}.md").write_text(notes, encoding="utf-8")
        return EXIT_OK

    def _manifest() -> int:
        write_release_manifest(
            REPO_ROOT,
            version,
            published_at,
            breaking=args.breaking,
            migration=args.migration,
            provenance=_provenance_from_args(args),
        )
        return EXIT_OK

    steps: list[tuple[str, object]] = [
        (
            f"write {notes_rel} (release notes from the CHANGELOG section)",
            _write_notes,
        ),
        (
            f'git tag -a {ref} -m "Template release {ref}"',
            lambda: _git_step(
                ["git", "tag", "-a", ref, "-m", f"Template release {ref}"]
            ),
        ),
        (
            f"git push origin {ref}",
            lambda: _git_step(["git", "push", "origin", ref]),
        ),
        (
            f"gh release create {ref} --title {ref} --notes-file {notes_rel}",
            lambda: _git_step(
                [
                    "gh",
                    "release",
                    "create",
                    ref,
                    "--title",
                    ref,
                    "--notes-file",
                    notes_rel,
                ]
            ),
        ),
        (
            f"write {manifest_rel} (release manifest, published_at={published_at})",
            _manifest,
        ),
        (
            f"gh release upload {ref} {manifest_rel}",
            lambda: _git_step(["gh", "release", "upload", ref, manifest_rel]),
        ),
    ]
    _print_plan(f"Publish plan for {ref}:", [label for label, _ in steps])
    if args.dry_run:
        print("\n👉 Dry run — nothing executed.")
        return EXIT_OK
    if not _confirm(f"Publish {ref}?", yes=args.yes):
        print("Aborted; nothing was executed.")
        return EXIT_PRECONDITION
    return _execute_steps(
        steps,
        f"{ref} published: tag, GitHub Release, and manifest asset are live.",
    )


def cmd_prepare(args: argparse.Namespace) -> int:
    version = prepare_release(REPO_ROOT, args.version, args.base_ref)
    ref = f"v{version}"
    branch = f"release/{ref}"
    print(f"✅ Prepared release {version} (Step 2):")
    print(f'   · pyproject.toml     -> version = "{version}"')
    print(
        f"   · CHANGELOG.md       -> new '## [{version}]' section (edit the bullets!)"
    )
    print("\n📝 Review the CHANGELOG bullets — they are raw commit subjects, turn")
    print("   them into human release notes. Then ship the bump with ONE command:")
    print("   make release-pr")
    print(f"   (creates {branch}, commits the bump, pushes, opens the PR)")
    print("\n   After the merge, on main: make publish-release")
    return EXIT_OK


def _add_provenance_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--proposal", action="append", help="Proposal ID (repeatable).")
    parser.add_argument(
        "--issue", action="append", help="Source issue URL (repeatable)."
    )
    parser.add_argument("--pr", action="append", help="Source PR URL (repeatable).")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cs = sub.add_parser("change-summary", help="Classify changes; recommend a bump.")
    cs.add_argument("--base-ref", default=None, help="Default: latest tag.")
    cs.set_defaults(func=cmd_change_summary)

    ps = sub.add_parser("platform-summary", help="Report platform changes.")
    ps.add_argument("--base-ref", default=None, help="Default: latest tag.")
    ps.set_defaults(func=cmd_platform_summary)

    rc = sub.add_parser("release-check", help="Read-only release preflight.")
    rc.add_argument("--version", default=None, help="Default: pyproject version.")
    rc.add_argument("--base-ref", default=None, help="Default: latest tag.")
    rc.add_argument("--require-provenance", action="store_true")
    rc.add_argument("--allow-platform", action="store_true")
    rc.add_argument(
        "--skip-gates", action="store_true", help="Skip make check/check-sync."
    )
    rc.add_argument("--skip-git", action="store_true", help="Skip dirty-tree check.")
    _add_provenance_args(rc)
    rc.set_defaults(func=cmd_release_check)

    rm = sub.add_parser("release-manifest", help="Generate the release asset.")
    rm.add_argument("--version", required=True)
    rm.add_argument("--published-at", required=True, help="ISO-8601 timestamp.")
    rm.add_argument("--breaking", action="store_true")
    rm.add_argument("--migration", default=None, help="Migration document path/URL.")
    _add_provenance_args(rm)
    rm.set_defaults(func=cmd_release_manifest)

    pp = sub.add_parser(
        "prepare", help="Step 2: write version into pyproject + CHANGELOG (local-only)."
    )
    pp.add_argument(
        "--version", default=None, help="Target X.Y.Z; default: recommended bump."
    )
    pp.add_argument("--base-ref", default=None, help="Base tag; default: latest tag.")
    pp.set_defaults(func=cmd_prepare)

    rl = sub.add_parser("release", help="Preflight + print manual publish steps.")
    rl.add_argument("--version", default=None, help="Default: pyproject version.")
    rl.add_argument("--base-ref", default=None, help="Default: latest tag.")
    rl.add_argument("--require-provenance", action="store_true")
    rl.add_argument("--allow-platform", action="store_true")
    rl.add_argument("--skip-gates", action="store_true")
    _add_provenance_args(rl)
    rl.set_defaults(func=cmd_release)

    rp = sub.add_parser(
        "release-pr",
        help="Guarded: branch + commit the version bump + push + open the PR.",
    )
    rp.add_argument("--version", default=None, help="Default: pyproject version.")
    rp.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    rp.add_argument(
        "--dry-run", action="store_true", help="Guards + plan only; execute nothing."
    )
    rp.set_defaults(func=cmd_release_pr)

    pb = sub.add_parser(
        "publish",
        help="Guarded: preflight, then tag + push + GitHub Release + manifest.",
    )
    pb.add_argument("--version", default=None, help="Default: pyproject version.")
    pb.add_argument("--base-ref", default=None, help="Default: latest tag.")
    pb.add_argument("--require-provenance", action="store_true")
    pb.add_argument("--allow-platform", action="store_true")
    pb.add_argument("--skip-gates", action="store_true")
    pb.add_argument("--breaking", action="store_true")
    pb.add_argument("--migration", default=None, help="Migration document path/URL.")
    pb.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    pb.add_argument(
        "--dry-run", action="store_true", help="Guards + plan only; execute nothing."
    )
    _add_provenance_args(pb)
    pb.set_defaults(func=cmd_publish)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return int(args.func(args))
    except ReleaseError as exc:
        print(f"❌ {exc}")
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
