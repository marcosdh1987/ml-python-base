"""Golden tests for skills-lock.json rendering and timestamp stability."""

from __future__ import annotations

from pathlib import Path

from ml_python_base.skills_sync.lockfile import LOCK_FILE, render_lock


def test_render_lock_matches_committed_byte_for_byte(repo_root: Path) -> None:
    committed = (repo_root / LOCK_FILE).read_text(encoding="utf-8")
    # A clearly different "now" proves timestamps are preserved when nothing
    # changed (the rendered output must still equal the committed file).
    rendered = render_lock(repo_root, now_iso="2099-01-01T00:00:00Z")
    assert rendered == committed


def test_render_lock_refreshes_timestamp_on_change(tmp_path: Path) -> None:
    external = tmp_path / ".github/skills-external/demo"
    external.mkdir(parents=True)
    (external / "SKILL.md").write_text("hello", encoding="utf-8")

    rendered = render_lock(tmp_path, now_iso="2099-01-01T00:00:00Z")
    assert '"generatedAt": "2099-01-01T00:00:00Z"' in rendered
    assert '"demo"' in rendered
    assert '"path": ".github/skills-external/demo"' in rendered
    assert rendered.endswith("}\n")


def test_render_lock_records_provenance_from_registry(tmp_path: Path) -> None:
    external = tmp_path / ".github/skills-external/demo"
    external.mkdir(parents=True)
    (external / "SKILL.md").write_text("hello", encoding="utf-8")

    rendered = render_lock(
        tmp_path,
        now_iso="2099-01-01T00:00:00Z",
        provenance={"demo": {"upstream": "https://example.test/x", "license": "MIT"}},
    )
    assert '"upstream": "https://example.test/x"' in rendered
    assert '"license": "MIT"' in rendered


def test_render_lock_marks_unknown_provenance(tmp_path: Path) -> None:
    """An undeclared origin must be visible in the lock, not silently omitted."""
    external = tmp_path / ".github/skills-external/mystery"
    external.mkdir(parents=True)
    (external / "SKILL.md").write_text("hello", encoding="utf-8")

    rendered = render_lock(tmp_path, now_iso="2099-01-01T00:00:00Z", provenance={})
    assert '"upstream": "UNKNOWN"' in rendered
    assert '"license": "UNKNOWN"' in rendered
