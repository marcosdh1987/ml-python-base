"""Tests for scripts/harness_release.py — the traceable release contract.

The release CLI is a maintenance script (like scripts/template_sync.py), so it is
loaded by path rather than imported as a package. Behaviour is exercised against
miniature temporary git repositories to keep the checks honest end-to-end.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/harness_release.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("harness_release", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses can resolve string annotations
    # (from __future__ import annotations) via the module namespace.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hr = _load_script()


# --------------------------------------------------------------------------- #
# Miniature repo fixtures
# --------------------------------------------------------------------------- #

_GIT_ENV = {
    "PATH": "/usr/bin:/bin:/usr/local/bin",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
}


def _git(root: Path, *args: str) -> str:
    env = dict(_GIT_ENV)
    env["HOME"] = str(root)
    out = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return out.stdout.strip()


def _configure_identity(root: Path) -> None:
    """Persist identity in the repo's local config so git commands run by the
    script under test (which inherit the real environment, e.g. a CI runner
    with no global config) can create commits and annotated tags."""
    _git(root, "config", "user.name", "t")
    _git(root, "config", "user.email", "t@t")


_REGISTRY = """\
schema_version = 1

[template_sync]
protocol = 1
governance_paths = [
    ".github/skills",
    ".github/architecture.md",
    "adapters/templates",
]
platform_paths = [
    "src/ml_python_base/skills_sync",
    "Makefile",
    "adapters/registry.toml",
    "pyproject.toml",
]
"""


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _set_version(root: Path, version: str) -> None:
    _write(
        root,
        "pyproject.toml",
        f'[project]\nname = "ml-python-base"\nversion = "{version}"\n',
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A miniature template repo at version 0.2.0 with one governance + one
    platform file, committed as the base revision."""
    root = tmp_path / "repo"
    root.mkdir()
    _set_version(root, "0.2.0")
    _write(
        root,
        "CHANGELOG.md",
        "# Changelog\n\n## [0.2.0]\n\n### Added\n- Baseline.\n\n## [0.1.0]\n\n### Added\n- Init.\n",
    )
    _write(root, "adapters/registry.toml", _REGISTRY)
    _write(root, ".github/architecture.md", "# Architecture\nv1\n")
    _write(root, "Makefile", "check:\n\t@echo ok\n")
    _git(root, "init", "-q")
    _configure_identity(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


def _base_sha(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD")


# --------------------------------------------------------------------------- #
# SemVer
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("v", ["0.2.0", "1.0.0", "10.20.30"])
def test_parse_semver_valid(v: str) -> None:
    assert hr.parse_semver(v) == tuple(int(x) for x in v.split("."))


@pytest.mark.parametrize("v", ["0.2", "v0.2.0", "0.2.0-rc1", "1.2.3.4", "abc", ""])
def test_parse_semver_invalid(v: str) -> None:
    with pytest.raises(hr.ReleaseError) as exc:
        hr.parse_semver(v)
    assert exc.value.exit_code == hr.EXIT_INVALID


def test_is_valid_semver() -> None:
    assert hr.is_valid_semver("1.2.3")
    assert not hr.is_valid_semver("v1.2.3")


# --------------------------------------------------------------------------- #
# Repository readers
# --------------------------------------------------------------------------- #


def test_read_pyproject_version(repo: Path) -> None:
    assert hr.read_pyproject_version(repo) == "0.2.0"


def test_changelog_has_section(repo: Path) -> None:
    assert hr.changelog_has_section(repo, "0.2.0")
    assert hr.changelog_has_section(repo, "0.1.0")
    assert not hr.changelog_has_section(repo, "0.3.0")


def test_tag_exists(repo: Path) -> None:
    assert not hr.tag_exists(repo, "0.2.0")
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    assert hr.tag_exists(repo, "0.2.0")


def test_working_tree_clean(repo: Path) -> None:
    assert hr.working_tree_clean(repo)
    _write(repo, "dirty.txt", "x")
    assert not hr.working_tree_clean(repo)


def test_load_sync_policy(repo: Path) -> None:
    governance, platform, protocol = hr.load_sync_policy(repo)
    assert protocol == 1
    assert ".github/architecture.md" in governance
    assert "Makefile" in platform


# --------------------------------------------------------------------------- #
# Classification and SemVer recommendation
# --------------------------------------------------------------------------- #


def test_classify_paths_buckets() -> None:
    gov = [".github/skills", ".github/architecture.md", "adapters/templates"]
    plat = ["Makefile", "pyproject.toml"]
    c = hr.classify_paths(
        [
            ("M", ".github/architecture.md"),
            ("A", ".github/skills/new.md"),
            ("M", "Makefile"),
            ("D", "adapters/templates/old.j2"),
            ("M", "README.md"),
        ],
        gov,
        plat,
    )
    assert ".github/architecture.md" in c.governance
    assert ".github/skills/new.md" in c.governance
    assert "Makefile" in c.platform
    assert "README.md" in c.other
    assert "adapters/templates/old.j2" in c.removed


def test_recommend_bump() -> None:
    gov = [".github/skills"]
    plat = ["Makefile"]
    # additive governance → minor
    add = hr.classify_paths([("A", ".github/skills/new.md")], gov, plat)
    assert hr.recommend_bump(add) == "minor"
    # removal → major
    rm = hr.classify_paths([("D", ".github/skills/old.md")], gov, plat)
    assert hr.recommend_bump(rm) == "major"
    # platform change → major (contract/layout risk)
    pf = hr.classify_paths([("M", "Makefile")], gov, plat)
    assert hr.recommend_bump(pf) == "major"
    # doc-only edit outside governance/platform → patch
    doc = hr.classify_paths([("M", "README.md")], gov, plat)
    assert hr.recommend_bump(doc) == "patch"


def test_bump_version() -> None:
    assert hr.bump_version("0.2.0", "patch") == "0.2.1"
    assert hr.bump_version("0.2.0", "minor") == "0.3.0"
    assert hr.bump_version("0.2.5", "major") == "1.0.0"


def test_changed_paths_reads_name_status(repo: Path) -> None:
    base = _base_sha(repo)
    _write(repo, ".github/architecture.md", "# Architecture\nv2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "edit gov")
    changed = hr.changed_paths(repo, base)
    assert ("M", ".github/architecture.md") in changed


# --------------------------------------------------------------------------- #
# check_release — the five mandated failing scenarios + a passing one
# --------------------------------------------------------------------------- #


def _codes(problems: list) -> set[str]:
    return {p.code for p in problems}


def test_check_release_invalid_semver(repo: Path) -> None:
    problems = hr.check_release(repo, "0.2", check_git=False)
    assert "invalid_semver" in _codes(problems)
    assert any(p.exit_code == hr.EXIT_INVALID for p in problems)


def test_check_release_version_changelog_mismatch(repo: Path) -> None:
    # pyproject is 0.2.0 but we ask to release 0.3.0 (changelog has the section).
    _write(
        repo,
        "CHANGELOG.md",
        "# Changelog\n\n## [0.3.0]\n\n### Added\n- x.\n\n## [0.2.0]\n\n### Added\n- b.\n",
    )
    problems = hr.check_release(repo, "0.3.0", check_git=False)
    assert "version_mismatch" in _codes(problems)


def test_check_release_changelog_missing(repo: Path) -> None:
    _set_version(repo, "0.3.0")  # aligned with request, but no changelog section
    problems = hr.check_release(repo, "0.3.0", check_git=False)
    assert "changelog_missing" in _codes(problems)


def test_check_release_tag_exists(repo: Path) -> None:
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    problems = hr.check_release(repo, "0.2.0", check_git=False)
    assert "tag_exists" in _codes(problems)
    assert any(
        p.exit_code == hr.EXIT_PRECONDITION for p in problems if p.code == "tag_exists"
    )


def test_check_release_missing_provenance(repo: Path) -> None:
    base = _base_sha(repo)
    _write(repo, ".github/architecture.md", "# Architecture\nv2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "gov change")
    problems = hr.check_release(
        repo, "0.2.0", base_ref=base, require_provenance=True, check_git=False
    )
    assert "provenance_missing" in _codes(problems)


def test_check_release_provenance_supplied_ok(repo: Path) -> None:
    base = _base_sha(repo)
    _write(repo, ".github/architecture.md", "# Architecture\nv2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "gov change")
    prov = hr.Provenance(
        proposals=("HEP-2026-014",),
        source_issues=("marcosdh1987/ml-python-base#31",),
        source_pull_requests=("marcosdh1987/ml-python-base#32",),
    )
    problems = hr.check_release(
        repo,
        "0.2.0",
        base_ref=base,
        provenance=prov,
        require_provenance=True,
        check_git=False,
    )
    assert "provenance_missing" not in _codes(problems)


def test_check_release_incompatible_platform_change(repo: Path) -> None:
    base = _base_sha(repo)
    _write(repo, "Makefile", "check:\n\t@echo changed\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "platform change")
    problems = hr.check_release(repo, "0.2.0", base_ref=base, check_git=False)
    codes = _codes(problems)
    assert "platform_change" in codes
    assert any(
        p.exit_code == hr.EXIT_INCOMPAT for p in problems if p.code == "platform_change"
    )


def test_check_release_platform_change_allowed(repo: Path) -> None:
    base = _base_sha(repo)
    _write(repo, "Makefile", "check:\n\t@echo changed\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "platform change")
    problems = hr.check_release(
        repo, "0.2.0", base_ref=base, allow_platform=True, check_git=False
    )
    assert "platform_change" not in _codes(problems)


def test_check_release_dirty_tree(repo: Path) -> None:
    _write(repo, "untracked.txt", "x")
    problems = hr.check_release(repo, "0.2.0", check_git=True)
    assert "dirty_tree" in _codes(problems)


def test_check_release_clean_pass(repo: Path) -> None:
    problems = hr.check_release(repo, "0.2.0", check_git=True)
    assert [p for p in problems if p.severity == "error"] == []


# --------------------------------------------------------------------------- #
# Release preparation (prepare / Step 2)
# --------------------------------------------------------------------------- #


def test_prepare_release_explicit_version(repo: Path) -> None:
    version = hr.prepare_release(repo, "0.3.0", None)
    assert version == "0.3.0"
    assert hr.read_pyproject_version(repo) == "0.3.0"
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    # New section sits above the previous one.
    assert text.index("## [0.3.0]") < text.index("## [0.2.0]")


def test_prepare_release_derives_version_and_bullets(repo: Path) -> None:
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    _write(repo, ".github/architecture.md", "# Architecture\nv2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat(governance): tighten the rules")
    version = hr.prepare_release(repo, None, None)
    # Governance-only change since v0.2.0 → recommended MINOR bump.
    assert version == "0.3.0"
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- feat(governance): tighten the rules" in text


def test_prepare_release_rejects_non_increasing(repo: Path) -> None:
    for bad in ("0.2.0", "0.1.9"):
        with pytest.raises(hr.ReleaseError) as exc:
            hr.prepare_release(repo, bad, None)
        assert exc.value.exit_code == hr.EXIT_PRECONDITION


def test_prepare_release_rejects_existing_tag_without_mutating(repo: Path) -> None:
    _git(repo, "tag", "-a", "v0.3.0", "-m", "r")
    with pytest.raises(hr.ReleaseError) as exc:
        hr.prepare_release(repo, "0.3.0", None)
    assert exc.value.exit_code == hr.EXIT_PRECONDITION
    # Precondition failures must leave both files untouched.
    assert hr.read_pyproject_version(repo) == "0.2.0"
    assert not hr.changelog_has_section(repo, "0.3.0")


def test_prepare_release_rejects_existing_changelog_section(repo: Path) -> None:
    with pytest.raises(hr.ReleaseError) as exc:
        hr.prepare_release(repo, "0.2.0", None)  # section [0.2.0] already exists
    assert exc.value.exit_code == hr.EXIT_PRECONDITION


def test_prepare_release_no_version_no_tag_errors(repo: Path) -> None:
    with pytest.raises(hr.ReleaseError) as exc:
        hr.prepare_release(repo, None, None)
    assert exc.value.exit_code == hr.EXIT_PRECONDITION


def test_prepare_release_placeholder_bullet_without_base(repo: Path) -> None:
    hr.prepare_release(repo, "0.3.0", None)  # no tags → no commit bullets
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- TODO: describe the changes in this release." in text


def test_cli_prepare(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["prepare", "--version", "0.3.0"])
    assert rc == hr.EXIT_OK
    assert hr.read_pyproject_version(repo) == "0.3.0"


def test_cli_prepare_precondition_exit_code(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["prepare", "--version", "0.1.0"])
    assert rc == hr.EXIT_PRECONDITION


# --------------------------------------------------------------------------- #
# Release manifest + schema
# --------------------------------------------------------------------------- #


def _valid_manifest() -> dict:
    return hr.build_release_manifest(
        repository="marcosdh1987/ml-python-base",
        version="0.2.0",
        commit="a" * 40,
        published_at="2026-07-22T15:00:00Z",
        sync_protocol=1,
        min_consumer_protocol=1,
        breaking=False,
        migration_document=None,
        governance_paths=[".github/skills", ".github/architecture.md"],
        platform_changed=False,
        platform_paths=[],
        proposals=["HEP-2026-014"],
        source_issues=["marcosdh1987/ml-python-base#31"],
        source_pull_requests=["marcosdh1987/ml-python-base#32"],
        governance_tree_sha256="sha256:" + "b" * 64,
        skills_lock_sha256="sha256:" + "c" * 64,
        registry_sha256="sha256:" + "d" * 64,
    )


def test_build_manifest_shape() -> None:
    m = _valid_manifest()
    assert m["schema_version"] == 1
    assert m["release"]["version"] == "0.2.0"
    assert m["release"]["ref"] == "v0.2.0"
    assert m["compatibility"]["sync_protocol"] == 1
    assert m["provenance"]["proposals"] == ["HEP-2026-014"]


def test_schema_file_is_valid_json() -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas/harness-release-v1.schema.json").read_text()
    )
    assert schema["$schema"]
    assert schema["type"] == "object"


def test_valid_manifest_passes_schema() -> None:
    schema = hr.load_schema()
    assert hr.validate_manifest(_valid_manifest(), schema) == []


def test_invalid_manifest_fails_schema() -> None:
    schema = hr.load_schema()
    m = _valid_manifest()
    del m["release"]["commit"]  # required field
    errors = hr.validate_manifest(m, schema)
    assert errors
    assert any("commit" in e for e in errors)


def test_manifest_wrong_type_fails_schema() -> None:
    schema = hr.load_schema()
    m = _valid_manifest()
    m["schema_version"] = "1"  # must be integer
    errors = hr.validate_manifest(m, schema)
    assert errors


# --------------------------------------------------------------------------- #
# YAML serialization
# --------------------------------------------------------------------------- #


def test_serialize_yaml_deterministic() -> None:
    data = {
        "schema_version": 1,
        "release": {"version": "0.2.0", "breaking": False, "migration_document": None},
        "provenance": {"proposals": ["HEP-2026-014"], "source_issues": []},
    }
    text = hr.serialize_yaml(data)
    assert "schema_version: 1" in text
    assert "  version: 0.2.0" in text
    assert "  breaking: false" in text
    assert "  migration_document: null" in text
    assert "    - HEP-2026-014" in text
    assert "source_issues: []" in text
    # Deterministic: same input → identical output.
    assert hr.serialize_yaml(data) == text


# --------------------------------------------------------------------------- #
# CLI wiring — exit codes
# --------------------------------------------------------------------------- #


def test_cli_release_check_pass(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["release-check", "--version", "0.2.0", "--skip-gates"])
    assert rc == hr.EXIT_OK


def test_cli_release_check_invalid_semver(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["release-check", "--version", "0.2", "--skip-gates"])
    assert rc == hr.EXIT_INVALID


def test_cli_release_check_tag_exists(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    rc = hr.main(["release-check", "--version", "0.2.0", "--skip-gates"])
    assert rc == hr.EXIT_PRECONDITION


def test_cli_change_summary(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    base = _base_sha(repo)
    _write(repo, ".github/architecture.md", "# Architecture\nv2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "gov")
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["change-summary", "--base-ref", base])
    assert rc == hr.EXIT_OK
    out = capsys.readouterr().out
    assert "minor" in out.lower()


# --------------------------------------------------------------------------- #
# Auto-defaults, pending release, and the bump-pair auto-allow
# --------------------------------------------------------------------------- #


def test_cli_release_check_defaults_version_from_pyproject(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["release-check", "--skip-gates"])
    assert rc == hr.EXIT_OK
    assert "using pyproject.toml: 0.2.0" in capsys.readouterr().out


def test_cli_release_check_defaults_base_ref_from_latest_tag(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _git(repo, "tag", "-a", "v0.1.0", "-m", "r")
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["release-check", "--skip-gates"])
    assert rc == hr.EXIT_OK
    assert "using latest tag: v0.1.0" in capsys.readouterr().out


def test_check_release_bump_pair_auto_allowed(repo: Path) -> None:
    base = _base_sha(repo)
    _set_version(repo, "0.3.0")
    _write(
        repo,
        "CHANGELOG.md",
        "# Changelog\n\n## [0.3.0]\n\n### Added\n- x.\n\n## [0.2.0]\n\n### Added\n- b.\n",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "bump")
    # pyproject.toml is a platform path, but the delta is exactly the bump pair.
    problems = hr.check_release(repo, "0.3.0", base_ref=base, check_git=False)
    assert "platform_change" not in _codes(problems)


def test_check_release_other_platform_path_still_fails(repo: Path) -> None:
    base = _base_sha(repo)
    _set_version(repo, "0.3.0")
    _write(
        repo,
        "CHANGELOG.md",
        "# Changelog\n\n## [0.3.0]\n\n### Added\n- x.\n\n## [0.2.0]\n\n### Added\n- b.\n",
    )
    _write(repo, "Makefile", "check:\n\t@echo changed\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "bump + platform")
    problems = hr.check_release(repo, "0.3.0", base_ref=base, check_git=False)
    assert "platform_change" in _codes(problems)


def test_pending_release_detected(repo: Path) -> None:
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    _set_version(repo, "0.3.0")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "bump only")
    assert hr.pending_release(repo) == "0.3.0"


def test_pending_release_none_when_current_is_tagged(repo: Path) -> None:
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    assert hr.pending_release(repo) is None


def test_prepare_refuses_pending_release(repo: Path) -> None:
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    _set_version(repo, "0.3.0")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "bump only")
    with pytest.raises(hr.ReleaseError) as exc:
        hr.prepare_release(repo, None, None)
    assert exc.value.exit_code == hr.EXIT_PRECONDITION
    assert "publish it first" in str(exc.value)
    # An explicit version overrides the guard.
    assert hr.prepare_release(repo, "0.4.0", None) == "0.4.0"


def test_cli_change_summary_warns_about_pending_release(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _git(repo, "tag", "-a", "v0.2.0", "-m", "r")
    _set_version(repo, "0.3.0")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "bump only")
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    rc = hr.main(["change-summary"])
    assert rc == hr.EXIT_OK
    out = capsys.readouterr().out
    assert "publish-release" in out


def test_extract_changelog_section(repo: Path) -> None:
    body = hr.extract_changelog_section(repo, "0.2.0")
    assert "- Baseline." in body
    assert "## [0.1.0]" not in body
    with pytest.raises(hr.ReleaseError):
        hr.extract_changelog_section(repo, "9.9.9")


# --------------------------------------------------------------------------- #
# Guarded subcommands: release-pr and publish
# --------------------------------------------------------------------------- #

_ORIG_RUN = hr.run


def _intercepting_runner(
    recorded: list[list[str]],
    fake_git_subcmds: set[str],
    fail_on: tuple[str, ...] = (),
):
    """Fake gh + selected git mutations (recording them); delegate reads to git."""

    def runner(cmd, root=None, *, check=True, capture=False):
        is_fake = cmd[0] == "gh" or (cmd[0] == "git" and cmd[1] in fake_git_subcmds)
        if is_fake:
            recorded.append(list(cmd))
            rc = 1 if fail_on and cmd[: len(fail_on)] == list(fail_on) else 0
            return subprocess.CompletedProcess(cmd, rc, stdout="", stderr="")
        return _ORIG_RUN(cmd, root, check=check, capture=capture)

    return runner


def _stage_bump(repo: Path) -> None:
    """Leave the tree exactly as `make new-version` + curation would: the bump
    files dirty and a curated (no TODO) CHANGELOG section for 0.3.0."""
    _set_version(repo, "0.3.0")
    _write(
        repo,
        "CHANGELOG.md",
        "# Changelog\n\n## [0.3.0]\n\n### Added\n- Curated note.\n\n"
        "## [0.2.0]\n\n### Added\n- Baseline.\n",
    )
    _write(repo, "uv.lock", "# lock\n")


def test_release_pr_refuses_clean_tree(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    rc = hr.main(["release-pr", "--yes"])
    assert rc == hr.EXIT_PRECONDITION


def test_release_pr_refuses_todo_bullet(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stage_bump(repo)
    _write(
        repo,
        "CHANGELOG.md",
        "# Changelog\n\n## [0.3.0]\n\n### Changed\n"
        "- TODO: describe the changes in this release.\n\n"
        "## [0.2.0]\n\n### Added\n- Baseline.\n",
    )
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    rc = hr.main(["release-pr", "--yes"])
    assert rc == hr.EXIT_PRECONDITION
    assert "changelog_todo" in capsys.readouterr().out


def test_release_pr_refuses_unrelated_dirty_files(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stage_bump(repo)
    _write(repo, "src/extra.py", "x = 1\n")
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    rc = hr.main(["release-pr", "--yes"])
    assert rc == hr.EXIT_PRECONDITION
    assert "unexpected_dirty" in capsys.readouterr().out


def test_release_pr_refuses_without_gh(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stage_bump(repo)
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: None)
    rc = hr.main(["release-pr", "--yes"])
    assert rc == hr.EXIT_MISSING
    assert "gh_missing" in capsys.readouterr().out


def test_release_pr_dry_run_executes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stage_bump(repo)
    recorded: list[list[str]] = []
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(
        hr, "run", _intercepting_runner(recorded, {"switch", "add", "commit", "push"})
    )
    rc = hr.main(["release-pr", "--dry-run"])
    assert rc == hr.EXIT_OK
    assert recorded == []
    assert "Dry run" in capsys.readouterr().out
    assert not hr.working_tree_clean(repo)  # bump files still dirty


def test_release_pr_aborts_without_confirmation(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stage_bump(repo)
    recorded: list[list[str]] = []
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(
        hr, "run", _intercepting_runner(recorded, {"switch", "add", "commit", "push"})
    )
    # stdin is not a tty under pytest, and --yes is absent → refuse.
    rc = hr.main(["release-pr"])
    assert rc == hr.EXIT_PRECONDITION
    assert recorded == []


def test_release_pr_happy_path_command_order(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stage_bump(repo)
    recorded: list[list[str]] = []
    monkeypatch.setattr(hr, "REPO_ROOT", repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(
        hr, "run", _intercepting_runner(recorded, {"switch", "add", "commit", "push"})
    )
    rc = hr.main(["release-pr", "--yes"])
    assert rc == hr.EXIT_OK
    heads = [(c[0], c[1]) for c in recorded]
    assert heads == [
        ("git", "switch"),
        ("git", "add"),
        ("git", "commit"),
        ("git", "push"),
        ("gh", "pr"),
    ]
    assert recorded[0][:3] == ["git", "switch", "-c"]
    assert recorded[0][3] == "release/v0.3.0"
    assert "pyproject.toml" in recorded[1]
    assert "CHANGELOG.md" in recorded[1]
    assert "uv.lock" in recorded[1]
    assert "chore(release): reconcile version and changelog for 0.3.0" in recorded[2]


@pytest.fixture
def publish_repo(tmp_path: Path) -> Path:
    """A repo on branch `main`, in sync with a local bare `origin`, carrying a
    merged 0.3.0 bump and everything the manifest needs at the tag."""
    root = tmp_path / "repo"
    root.mkdir()
    _set_version(root, "0.3.0")
    _write(
        root,
        "CHANGELOG.md",
        "# Changelog\n\n## [0.3.0]\n\n### Added\n- Curated note.\n\n"
        "## [0.2.0]\n\n### Added\n- Baseline.\n",
    )
    _write(root, "adapters/registry.toml", _REGISTRY)
    _write(root, ".github/architecture.md", "# Architecture\nv1\n")
    _write(root, "Makefile", "check:\n\t@echo ok\n")
    _write(root, "skills-lock.json", "{}\n")
    _write(root, "uv.lock", "# lock\n")
    _git(root, "init", "-q")
    _configure_identity(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "merged bump")
    _git(root, "branch", "-m", "main")
    _git(root, "tag", "-a", "v0.2.0", "-m", "prev")
    bare = tmp_path / "origin.git"
    _git(root, "init", "-q", "--bare", str(bare))
    _git(root, "remote", "add", "origin", str(bare))
    _git(root, "push", "-q", "-u", "origin", "main")
    return root


def test_publish_refuses_off_main(
    publish_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _git(publish_repo, "switch", "-q", "-c", "feature/x")
    monkeypatch.setattr(hr, "REPO_ROOT", publish_repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    rc = hr.main(["publish", "--skip-gates", "--yes"])
    assert rc == hr.EXIT_PRECONDITION
    assert "off_main" in capsys.readouterr().out


def test_publish_refuses_out_of_sync(
    publish_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _write(publish_repo, ".github/architecture.md", "# Architecture\nv2\n")
    _git(publish_repo, "add", "-A")
    _git(publish_repo, "commit", "-q", "-m", "unpushed")
    monkeypatch.setattr(hr, "REPO_ROOT", publish_repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    rc = hr.main(["publish", "--skip-gates", "--yes"])
    assert rc == hr.EXIT_PRECONDITION
    assert "out_of_sync" in capsys.readouterr().out


def test_publish_dry_run_executes_nothing(
    publish_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    recorded: list[list[str]] = []
    monkeypatch.setattr(hr, "REPO_ROOT", publish_repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(hr, "run", _intercepting_runner(recorded, {"push"}))
    rc = hr.main(["publish", "--skip-gates", "--dry-run"])
    assert rc == hr.EXIT_OK
    assert recorded == []
    assert not hr.tag_exists(publish_repo, "0.3.0")
    assert "Dry run" in capsys.readouterr().out


def test_publish_happy_path(
    publish_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded: list[list[str]] = []
    monkeypatch.setattr(hr, "REPO_ROOT", publish_repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    # `git tag` runs for real (the manifest reads the tag); push + gh are faked.
    monkeypatch.setattr(hr, "run", _intercepting_runner(recorded, {"push"}))
    rc = hr.main(["publish", "--skip-gates", "--yes"])
    assert rc == hr.EXIT_OK
    assert hr.tag_exists(publish_repo, "0.3.0")
    heads = [(c[0], c[1]) for c in recorded]
    assert heads == [("git", "push"), ("gh", "release"), ("gh", "release")]
    assert recorded[1][2] == "create"
    assert recorded[2][2] == "upload"
    notes = (publish_repo / "dist/release-notes-v0.3.0.md").read_text()
    assert "- Curated note." in notes
    manifest = (publish_repo / "dist/harness-release-v0.3.0.yaml").read_text()
    assert "version: 0.3.0" in manifest
    assert "published_at:" in manifest


def test_publish_mid_failure_reports_remaining_steps(
    publish_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    recorded: list[list[str]] = []
    monkeypatch.setattr(hr, "REPO_ROOT", publish_repo)
    monkeypatch.setattr(hr.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(
        hr,
        "run",
        _intercepting_runner(recorded, {"push"}, fail_on=("gh", "release", "create")),
    )
    rc = hr.main(["publish", "--skip-gates", "--yes"])
    assert rc != hr.EXIT_OK
    out = capsys.readouterr().out
    # The tag survives (never rolled back) and the tail of the plan is printed.
    assert hr.tag_exists(publish_repo, "0.3.0")
    assert "NOT rolled back" in out
    assert "Finish manually" in out
    assert "gh release upload" in out
