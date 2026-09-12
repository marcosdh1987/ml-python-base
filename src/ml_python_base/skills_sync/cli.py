"""Command-line entrypoint for the skills sync engine.

Run via ``uv run python -m ml_python_base.skills_sync <command>``. The Makefile
delegates its skill targets here so the projection logic lives in one testable
place instead of duplicated bash.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ml_python_base.skills_sync.agents import (
    discover_agents,
    expected_agent_files,
    project_agents,
)
from ml_python_base.skills_sync.catalog import (
    assert_valid_catalog,
    catalog_warnings,
)
from ml_python_base.skills_sync.config import DEFAULT_REGISTRY_PATH, load_registry
from ml_python_base.skills_sync.discovery import EXTERNAL_DIR, discover_skills
from ml_python_base.skills_sync.errors import DriftError, SkillsSyncError
from ml_python_base.skills_sync.ingest import ingest_external_skills
from ml_python_base.skills_sync.linker import (
    expected_overlay_files,
    link_tool,
    stale_native_entries,
)
from ml_python_base.skills_sync.lockfile import LOCK_FILE, render_lock, write_lock
from ml_python_base.skills_sync.manifest import (
    read_manifest,
    render_manifest,
    write_manifest,
)
from ml_python_base.skills_sync.models import LINK_COPY, Registry, Skill, ToolSpec
from ml_python_base.skills_sync.renderer import (
    catalog_path,
    expected_file,
    render_catalog,
    render_tool,
    write_catalog,
)
from ml_python_base.skills_sync.routing import route

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_DRIFT = 2


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _selected_tools(registry: Registry, tool_id: str | None) -> list[ToolSpec]:
    if tool_id is None:
        return list(registry.tools)
    return [registry.tool(tool_id)]


def _skills(root: Path, registry: Registry) -> list[Skill]:
    """Discover skills with catalog metadata applied and validated."""
    skills = discover_skills(root, registry=registry)
    assert_valid_catalog(skills, registry)
    for warning in catalog_warnings(skills, registry):
        print(f"⚠️  catalog: {warning}", file=sys.stderr)
    return skills


def _do_link(root: Path, registry: Registry, tool_id: str | None) -> None:
    skills = _skills(root, registry)
    for tool in _selected_tools(registry, tool_id):
        hashes = link_tool(root, tool, skills)
        if tool.needs_manifest and tool.manifest_path:
            write_manifest(root / tool.manifest_path, hashes)
        if tool.has_native_view:
            print(f"🧩 linked {tool.display_name} -> {tool.native_skills_dir}/")


def _do_agents(root: Path, registry: Registry, tool_id: str | None) -> None:
    agents = discover_agents(root)
    for tool in _selected_tools(registry, tool_id):
        if not tool.has_agent_view:
            continue
        count = project_agents(root, tool, agents)
        print(f"🤖 projected {count} agents -> {tool.native_agents_dir}/")


def _do_render(root: Path, registry: Registry, tool_id: str | None) -> None:
    skills = _skills(root, registry)
    for tool in _selected_tools(registry, tool_id):
        if not tool.adapter_file:
            continue
        changed = render_tool(root, registry, tool, skills=skills)
        state = "updated" if changed else "unchanged"
        print(f"📝 {tool.adapter_file}: {state}")


def _do_catalog(root: Path, registry: Registry) -> None:
    path = catalog_path(root, registry)
    if path is None:
        print("note: registry declares no [catalog].output; nothing to write")
        return
    changed = write_catalog(root, registry, _skills(root, registry))
    state = "updated" if changed else "unchanged"
    print(f"📚 {registry.catalog.output}: {state}")


def _do_ingest(root: Path) -> None:
    result = ingest_external_skills(root)
    if not result.found_source:
        print("note: no ad-hoc skills source (.agents/skills or .agent/skills)")
    print(
        f"📦 ingest: synced={result.synced} skipped={result.skipped} "
        f"generated_skipped={result.generated_skipped}"
    )
    write_lock(root, _now_iso())
    print(f"🧾 lock file refreshed at {LOCK_FILE}")


def _do_sync(root: Path, registry: Registry) -> None:
    _do_ingest(root)
    _do_link(root, registry, None)
    _do_agents(root, registry, None)
    _do_render(root, registry, None)
    _do_catalog(root, registry)
    print("✅ sync complete (external ingested, native views + adapters refreshed)")


def _do_purge(root: Path, registry: Registry) -> None:
    for tool in registry.tools:
        if tool.native_skills_dir:
            shutil.rmtree(root / tool.native_skills_dir, ignore_errors=True)
    shutil.rmtree(root / EXTERNAL_DIR, ignore_errors=True)
    (root / LOCK_FILE).unlink(missing_ok=True)
    (root / EXTERNAL_DIR).mkdir(parents=True, exist_ok=True)
    _do_link(root, registry, None)
    _do_agents(root, registry, None)
    _do_render(root, registry, None)
    _do_catalog(root, registry)
    print("🧨 external skills purged; native views + adapters reset to internal")


def check_drift(root: Path, registry: Registry) -> list[str]:
    """Return the sorted stale artifact paths; empty when nothing has drifted.

    The programmatic half of the ``check`` command, so a caller that needs the
    result as data (a health panel, another repository's tooling) does not have
    to shell out and parse stdout. CI and that caller then share one
    implementation of what "stale" means.
    """
    skills = _skills(root, registry)
    agents = discover_agents(root)
    stale: list[str] = []

    for tool in registry.tools:
        # Adapter region drift.
        if tool.adapter_file:
            expected = expected_file(root, registry, tool)
            path = root / tool.adapter_file
            if expected is not None and path.read_text(encoding="utf-8") != expected:
                stale.append(tool.adapter_file)
        # Manifest drift (copy-strategy tools).
        if tool.needs_manifest and tool.manifest_path:
            desired = link_tool_dry(tool, skills, root)
            manifest_path = root / tool.manifest_path
            if render_manifest(desired) != render_manifest(
                read_manifest(manifest_path)
            ):
                stale.append(tool.manifest_path)
        # Generated overlay files (symlink tools) and entries that must not exist.
        for path, content in expected_overlay_files(root, tool, skills).items():
            actual = path.read_text(encoding="utf-8") if path.is_file() else ""
            if actual != content:
                stale.append(str(path.relative_to(root)))
        stale.extend(stale_native_entries(root, tool, skills))
        # Native agent projection drift.
        for path, content in expected_agent_files(root, tool, agents).items():
            actual = path.read_text(encoding="utf-8") if path.is_file() else ""
            if actual != content:
                stale.append(str(path.relative_to(root)))

    expected_lock = render_lock(root, _now_iso())
    lock_path = root / LOCK_FILE
    actual_lock = lock_path.read_text(encoding="utf-8") if lock_path.is_file() else ""
    if expected_lock != actual_lock:
        stale.append(str(LOCK_FILE))

    doc_path = catalog_path(root, registry)
    if doc_path is not None:
        actual_doc = doc_path.read_text(encoding="utf-8") if doc_path.is_file() else ""
        if actual_doc != render_catalog(root, registry, skills):
            stale.append(registry.catalog.output)

    return sorted(set(stale))


def _do_check(root: Path, registry: Registry) -> int:
    stale = check_drift(root, registry)
    if stale:
        raise DriftError(stale)
    print("✅ no skill-sync drift detected")
    return EXIT_OK


def _do_route(root: Path, registry: Registry, prompt: str) -> int:
    decision = route(prompt, _skills(root, registry), registry)
    print(json.dumps(decision.as_dict(), indent=2))
    return EXIT_OK


def link_tool_dry(
    tool: ToolSpec, skills: list[Skill], root: Path | None = None
) -> dict[str, str]:
    """Compute the manifest hashes a copy-tool *would* produce, without touching
    its live native dir (materializes into a throwaway temp dir).

    ``root`` must be the real repository root when any skill carries an overlay:
    the generated banner names the source path relative to it."""
    if tool.link_strategy != LINK_COPY:
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        clone = ToolSpec(
            id=tool.id,
            display_name=tool.display_name,
            link_strategy=tool.link_strategy,
            native_skills_dir=tmp,
            needs_manifest=False,
        )
        # native_skills_dir is absolute; link_tool joins root/dir, and joining an
        # absolute path discards the left operand, so the live tree is untouched.
        return link_tool(root or Path("/"), clone, skills)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skills_sync",
        description="Project governed skills + adapters into AI tool layouts.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Path to the tool registry (default: adapters/registry.toml).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    link = sub.add_parser("link", help="Materialize native skill views.")
    link.add_argument("--tool", help="Restrict to a single tool id.")

    render = sub.add_parser("render", help="Regenerate adapter skill regions.")
    render.add_argument("--tool", help="Restrict to a single tool id.")

    agents = sub.add_parser("agents", help="Project governed agents into tools.")
    agents.add_argument("--tool", help="Restrict to a single tool id.")

    sub.add_parser("catalog", help="Regenerate the skills catalog document.")
    sub.add_parser("ingest", help="Ingest ad-hoc skills into governed external.")
    sub.add_parser("sync", help="ingest + link + agents + render + catalog.")
    sub.add_parser("purge", help="Reset external skills + native views.")
    sub.add_parser("check", help="Fail if generated artifacts are stale.")

    route_cmd = sub.add_parser("route", help="Route a prompt through the catalog.")
    route_cmd.add_argument("prompt", help="The user request to route.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root: Path = args.root
    try:
        registry = load_registry(args.registry)
        if args.command == "link":
            _do_link(root, registry, args.tool)
        elif args.command == "render":
            _do_render(root, registry, args.tool)
        elif args.command == "agents":
            _do_agents(root, registry, args.tool)
        elif args.command == "catalog":
            _do_catalog(root, registry)
        elif args.command == "ingest":
            _do_ingest(root)
        elif args.command == "sync":
            _do_sync(root, registry)
        elif args.command == "purge":
            _do_purge(root, registry)
        elif args.command == "check":
            return _do_check(root, registry)
        elif args.command == "route":
            return _do_route(root, registry, args.prompt)
    except DriftError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_DRIFT
    except SkillsSyncError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
