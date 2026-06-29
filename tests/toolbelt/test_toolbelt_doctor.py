"""Tests for scripts/toolbelt_doctor.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/toolbelt_doctor.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("toolbelt_doctor", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


toolbelt_doctor = _load_script()


def _fake_which(installed: set[str]):
    def which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in installed else None

    return which


class _Response:
    def __init__(self, status: int = 200) -> None:
        self.status = status

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _size: int = -1) -> bytes:
        return b"{}"


def test_all_core_tools_present_returns_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    installed = {"git", "uv", "curl", "gh", "docker", "jq"}
    monkeypatch.setattr(toolbelt_doctor.shutil, "which", _fake_which(installed))

    assert toolbelt_doctor.main([]) == 0

    output = capsys.readouterr().out
    assert "git" in output
    assert "uv" in output
    assert "curl" in output
    assert "installed" in output


def test_missing_optional_tools_do_not_fail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        toolbelt_doctor.shutil, "which", _fake_which({"git", "uv", "curl"})
    )

    assert toolbelt_doctor.main([]) == 0

    output = capsys.readouterr().out
    assert "gh" in output
    assert "optional" in output
    assert "missing" in output


def test_missing_core_tool_returns_non_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(toolbelt_doctor.shutil, "which", _fake_which({"git", "uv"}))

    assert toolbelt_doctor.main([]) == 1

    output = capsys.readouterr().out
    assert "curl" in output
    assert "core" in output
    assert "missing" in output


def test_service_checks_run_only_when_configured(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        toolbelt_doctor.shutil, "which", _fake_which({"git", "uv", "curl"})
    )
    monkeypatch.delenv("GATEWAY_BASE_URL", raising=False)
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")
    checked_urls: list[str] = []

    def fake_urlopen(request: Any, timeout: float) -> _Response:
        checked_urls.append(request.full_url)
        assert timeout == 3.0
        return _Response()

    monkeypatch.setattr(toolbelt_doctor.request, "urlopen", fake_urlopen)

    assert toolbelt_doctor.main([]) == 0

    output = capsys.readouterr().out
    assert "GATEWAY_BASE_URL" in output
    assert "not configured" in output
    assert "LANGFUSE_HOST" in output
    assert "reachable" in output
    assert checked_urls == ["http://localhost:3000/api/public/health"]


def test_unreachable_optional_service_does_not_fail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        toolbelt_doctor.shutil, "which", _fake_which({"git", "uv", "curl"})
    )
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

    def fake_urlopen(_request: Any, timeout: float) -> _Response:
        assert timeout == 3.0
        raise OSError("connection refused")

    monkeypatch.setattr(toolbelt_doctor.request, "urlopen", fake_urlopen)

    assert toolbelt_doctor.main([]) == 0

    output = capsys.readouterr().out
    assert "MLFLOW_TRACKING_URI" in output
    assert "unreachable" in output
    assert "connection refused" in output
