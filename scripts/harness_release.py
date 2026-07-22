#!/usr/bin/env python3
"""Traceable template release contract — read-only preflight and manifest tooling.

This script never mutates git. It validates that a release is coherent, classifies
governance vs. platform changes, recommends a SemVer bump, generates the release
manifest asset (after the tag exists), and prints the exact manual commands an
operator runs to tag and publish. Tagging, pushing, and Release publication stay
manual — this tool only prepares and verifies.

Subcommands:
    change-summary    --base-ref REF        Classify changes and recommend a bump.
    platform-summary  --base-ref REF        Report platform changes + migration need.
    release-check     --version X.Y.Z       Read-only release preflight.
    release-manifest  --version X.Y.Z       Generate the release asset after tagging.
    release           --version X.Y.Z       Preflight + print manual tag/release steps.

Run via `make harness-release-check VERSION=0.2.0` etc. All subprocess calls pass
argument arrays (never a shell string). Governance and platform paths come from
adapters/registry.toml [template_sync] — a closed allowlist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tomllib
from dataclasses import dataclass
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
            problems.append(
                Problem(
                    "platform_change",
                    "Release changes platform paths "
                    f"({', '.join(classification.platform)}); platform changes need a "
                    "separate reviewed PR/release (pass --allow-platform to override).",
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


def _print_problems(problems: list[Problem]) -> int:
    errors = [p for p in problems if p.severity == "error"]
    for p in problems:
        icon = "❌" if p.severity == "error" else "⚠️ "
        print(f"{icon} [{p.code}] {p.message}")
    if errors:
        return errors[0].exit_code
    print("✅ Release preflight passed (read-only).")
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
    governance, platform, _ = load_sync_policy(REPO_ROOT)
    classification = classify_paths(
        changed_paths(REPO_ROOT, args.base_ref), governance, platform
    )
    bump = recommend_bump(classification)
    print(f"📊 Change summary since {args.base_ref}:")
    print(f"   governance: {len(classification.governance)} path(s)")
    print(f"   platform:   {len(classification.platform)} path(s)")
    print(f"   other:      {len(classification.other)} path(s)")
    print(f"   removed:    {len(classification.removed)} path(s)")
    print(f"👉 Recommended SemVer bump: {bump.upper()}")
    if classification.platform:
        print("   ⚠️  Platform paths changed — needs a separate reviewed PR/release.")
    return EXIT_OK


def cmd_platform_summary(args: argparse.Namespace) -> int:
    governance, platform, _ = load_sync_policy(REPO_ROOT)
    classification = classify_paths(
        changed_paths(REPO_ROOT, args.base_ref), governance, platform
    )
    if not classification.platform:
        print("✅ No platform-path changes; governance-only release is possible.")
        return EXIT_OK
    print("⚠️  Platform changes detected (require a migration note and MAJOR review):")
    for path in classification.platform:
        print(f"   · {path}")
    return EXIT_OK


def cmd_release_check(args: argparse.Namespace) -> int:
    problems = check_release(
        REPO_ROOT,
        args.version,
        base_ref=args.base_ref,
        provenance=_provenance_from_args(args),
        require_provenance=args.require_provenance,
        allow_platform=args.allow_platform,
        check_git=not args.skip_git,
    )
    if not args.skip_gates and not any(p.code == "invalid_semver" for p in problems):
        problems.extend(_run_gates())
    return _print_problems(problems)


def cmd_release_manifest(args: argparse.Namespace) -> int:
    if not is_valid_semver(args.version):
        print(f"❌ Invalid SemVer '{args.version}'.")
        return EXIT_INVALID
    ref = f"v{args.version}"
    if not tag_exists(REPO_ROOT, args.version):
        print(f"❌ Tag '{ref}' does not exist yet. Create the tag before the manifest.")
        return EXIT_MISSING
    commit = run(["git", "rev-parse", ref], REPO_ROOT, capture=True).stdout.strip()
    governance, _platform, protocol = load_sync_policy(REPO_ROOT)
    manifest = build_release_manifest(
        repository=REPOSITORY,
        version=args.version,
        commit=commit,
        published_at=args.published_at,
        sync_protocol=protocol,
        min_consumer_protocol=protocol,
        breaking=args.breaking,
        migration_document=args.migration,
        governance_paths=governance,
        platform_changed=False,
        platform_paths=[],
        proposals=list(args.proposal or ()),
        source_issues=list(args.issue or ()),
        source_pull_requests=list(args.pr or ()),
        governance_tree_sha256=hash_tree_at_ref(REPO_ROOT, governance, ref),
        skills_lock_sha256=hash_file_at_ref(REPO_ROOT, "skills-lock.json", ref),
        registry_sha256=hash_file_at_ref(REPO_ROOT, "adapters/registry.toml", ref),
    )
    errors = validate_manifest(manifest, load_schema())
    if errors:
        print("❌ Generated manifest failed schema validation:")
        for e in errors:
            print(f"   · {e}")
        return EXIT_INVALID
    out_path = REPO_ROOT / f"harness-release-{ref}.yaml"
    out_path.write_text(serialize_yaml(manifest), encoding="utf-8")
    print(f"✅ Wrote release manifest: {out_path.name}")
    print(f"   Attach it manually to the GitHub Release for {ref}.")
    return EXIT_OK


def cmd_release(args: argparse.Namespace) -> int:
    problems = check_release(
        REPO_ROOT,
        args.version,
        base_ref=args.base_ref,
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
    ref = f"v{args.version}"
    print("\n📋 Preflight passed. Run these commands MANUALLY to publish:")
    print(f'   git tag -a {ref} -m "Template release {ref}"')
    print(f"   git push origin {ref}")
    print(f"   gh release create {ref} --title {ref} --notes-file <release-notes.md>")
    print(f"   make harness-release-manifest VERSION={args.version}")
    print(f"   gh release upload {ref} harness-release-{ref}.yaml")
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
    cs.add_argument("--base-ref", required=True)
    cs.set_defaults(func=cmd_change_summary)

    ps = sub.add_parser("platform-summary", help="Report platform changes.")
    ps.add_argument("--base-ref", required=True)
    ps.set_defaults(func=cmd_platform_summary)

    rc = sub.add_parser("release-check", help="Read-only release preflight.")
    rc.add_argument("--version", required=True)
    rc.add_argument("--base-ref", default=None)
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

    rl = sub.add_parser("release", help="Preflight + print manual publish steps.")
    rl.add_argument("--version", required=True)
    rl.add_argument("--base-ref", default=None)
    rl.add_argument("--require-provenance", action="store_true")
    rl.add_argument("--allow-platform", action="store_true")
    rl.add_argument("--skip-gates", action="store_true")
    _add_provenance_args(rl)
    rl.set_defaults(func=cmd_release)

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
