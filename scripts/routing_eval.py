"""Skill-routing evaluation: deterministic report, or opt-in live model check.

Deterministic (default) — routes every scenario in ``tests/routing/scenarios.toml``
through the reference router and prints a pass/fail table. This is the same
check ``make routing-eval`` / ``make check`` run; the script exists so the report
can be read outside pytest and compared across catalog versions.

Live (``--live``) — asks a real model which skill it would invoke first for each
scenario, given only the generated skills block of one adapter file, and
compares the answer with the scenario's expectations. It shells out to the
``claude`` CLI (or ``opencode run``) so no SDK dependency is added; it is opt-in
because it costs tokens and is not deterministic. Use ``--adapter`` to point at
a different adapter file (or a saved copy of an older one) to compare catalog
versions side by side.

Usage::

    uv run python scripts/routing_eval.py                 # deterministic table
    uv run python scripts/routing_eval.py --live          # claude CLI, CLAUDE.md
    uv run python scripts/routing_eval.py --live --runner opencode --model gateway/x
    uv run python scripts/routing_eval.py --live --adapter /tmp/CLAUDE.old.md --out r.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ml_python_base.skills_sync.catalog import resolve_name  # noqa: E402
from ml_python_base.skills_sync.config import load_registry  # noqa: E402
from ml_python_base.skills_sync.discovery import discover_skills  # noqa: E402
from ml_python_base.skills_sync.renderer import BEGIN_MARKER, END_MARKER  # noqa: E402
from ml_python_base.skills_sync.routing import route  # noqa: E402

SCENARIOS = REPO_ROOT / "tests/routing/scenarios.toml"

LIVE_INSTRUCTIONS = (
    "You are an engineering agent working in a governed repository. Below is the "
    "skills section of your instructions, then a user request. Decide which ONE "
    "skill you would read and follow FIRST for that request. If no skill applies, "
    "answer null. Reply with JSON only, no prose: "
    '{"skill": "<name or null>", "mode": "<full|execute_only|local_model_32k|n/a>", '
    '"why": "<one short sentence>"}'
)


@dataclass
class Result:
    id: str
    prompt: str
    expected: list[str]
    forbidden: list[str]
    chosen: str | None
    resolved: str | None
    mode: str
    passed: bool
    forbidden_hit: bool
    ambiguous: bool
    note: str = ""


def load_scenarios() -> list[dict]:
    return tomllib.loads(SCENARIOS.read_text(encoding="utf-8"))["scenario"]


def judge(
    scenario: dict, chosen: str | None, resolved: str | None, mode: str
) -> tuple[bool, bool]:
    expect_none = bool(scenario.get("expect_none"))
    forbidden_hit = chosen in scenario["forbidden_skills"] or (
        resolved in scenario["forbidden_skills"]
    )
    passed = chosen is None if expect_none else resolved in scenario["expected_skills"]
    if "expected_mode" in scenario and mode not in ("n/a", ""):
        passed = passed and mode == scenario["expected_mode"]
    return passed and not forbidden_hit, forbidden_hit


def run_deterministic(scenarios: list[dict]) -> list[Result]:
    registry = load_registry(REPO_ROOT / "adapters/registry.toml")
    skills = discover_skills(REPO_ROOT, registry=registry)
    results: list[Result] = []
    for scenario in scenarios:
        decision = route(scenario["prompt"], skills, registry)
        passed, forbidden_hit = judge(
            scenario, decision.skill, decision.skill, decision.mode
        )
        results.append(
            Result(
                id=scenario["id"],
                prompt=scenario["prompt"],
                expected=scenario["expected_skills"],
                forbidden=scenario["forbidden_skills"],
                chosen=decision.skill,
                resolved=decision.skill,
                mode=decision.mode,
                passed=passed,
                forbidden_hit=forbidden_hit,
                ambiguous=decision.ambiguous,
                note=", ".join(decision.matched),
            )
        )
    return results


def skills_block(adapter: Path) -> str:
    text = adapter.read_text(encoding="utf-8")
    if BEGIN_MARKER in text and END_MARKER in text:
        start = text.index(BEGIN_MARKER) + len(BEGIN_MARKER)
        return text[start : text.index(END_MARKER)].strip()
    return text


def ask_model(runner: str, model: str | None, prompt: str) -> str:
    if runner == "claude":
        cmd = ["claude", "-p", "--output-format", "text"]
        if model:
            cmd += ["--model", model]
        cmd.append(prompt)
    elif runner == "opencode":
        cmd = ["opencode", "run"]
        if model:
            cmd += ["--model", model]
        cmd.append(prompt)
    else:
        raise SystemExit(f"unknown runner: {runner}")
    if shutil.which(cmd[0]) is None:
        raise SystemExit(f"{cmd[0]} CLI not found on PATH")
    completed = subprocess.run(  # fixed argv, no shell
        cmd, capture_output=True, text=True, timeout=180, check=False
    )
    return completed.stdout.strip() or completed.stderr.strip()


def parse_answer(raw: str) -> tuple[str | None, str]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None, "n/a"
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None, "n/a"
    skill = data.get("skill")
    skill = None if skill in (None, "", "null", "none") else str(skill).strip("`")
    return skill, str(data.get("mode", "n/a"))


def run_live(
    scenarios: list[dict], runner: str, model: str | None, adapter: Path
) -> list[Result]:
    registry = load_registry(REPO_ROOT / "adapters/registry.toml")
    skills = discover_skills(REPO_ROOT, registry=registry)
    block = skills_block(adapter)
    results: list[Result] = []
    for scenario in scenarios:
        prompt = (
            f"{LIVE_INSTRUCTIONS}\n\n--- SKILLS SECTION ---\n{block}\n\n"
            f"--- USER REQUEST ---\n{scenario['prompt']}"
        )
        raw = ask_model(runner, model, prompt)
        chosen, mode = parse_answer(raw)
        resolved = resolve_name(chosen, skills, registry) if chosen else None
        passed, forbidden_hit = judge(scenario, chosen, resolved, mode)
        results.append(
            Result(
                id=scenario["id"],
                prompt=scenario["prompt"],
                expected=scenario["expected_skills"],
                forbidden=scenario["forbidden_skills"],
                chosen=chosen,
                resolved=resolved,
                mode=mode,
                passed=passed,
                forbidden_hit=forbidden_hit,
                ambiguous=False,
                note=raw[:160].replace("\n", " "),
            )
        )
        print(f"{'PASS' if passed else 'FAIL'}  {scenario['id']:34} -> {chosen}")
    return results


def print_table(results: list[Result], title: str) -> None:
    print(f"\n## {title}\n")
    print("| id | chosen | expected | mode | result |")
    print("|---|---|---|---|---|")
    for r in results:
        flag = "pass" if r.passed else ("FORBIDDEN" if r.forbidden_hit else "fail")
        print(
            f"| {r.id} | {r.chosen} | {', '.join(r.expected) or '—'} | {r.mode} | {flag} |"
        )
    passed = sum(1 for r in results if r.passed)
    forbidden = sum(1 for r in results if r.forbidden_hit)
    ambiguous = sum(1 for r in results if r.ambiguous)
    print(
        f"\n{passed}/{len(results)} passed · {forbidden} forbidden hits · "
        f"{ambiguous} ambiguous"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--live", action="store_true", help="ask a real model")
    parser.add_argument("--runner", default="claude", choices=("claude", "opencode"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--adapter", type=Path, default=REPO_ROOT / "CLAUDE.md")
    parser.add_argument("--only", default=None, help="comma-separated scenario ids")
    parser.add_argument("--out", type=Path, default=None, help="write JSON report")
    args = parser.parse_args(argv)

    scenarios = load_scenarios()
    if args.only:
        wanted = set(args.only.split(","))
        scenarios = [s for s in scenarios if s["id"] in wanted]

    if args.live:
        results = run_live(scenarios, args.runner, args.model, args.adapter)
        title = f"live routing eval · {args.runner} · {args.model or 'default'} · {args.adapter.name}"
    else:
        results = run_deterministic(scenarios)
        title = "deterministic routing eval"
    print_table(results, title)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {"title": title, "results": [asdict(r) for r in results]}, indent=2
            ),
            encoding="utf-8",
        )
        print(f"report written to {args.out}")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
