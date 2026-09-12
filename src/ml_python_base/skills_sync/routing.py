"""Deterministic reference router: prompt → skill, from catalog metadata alone.

This is not a model. It is the executable form of the routing rules the
adapter files state in prose, so the catalog can be tested in CI without an
LLM: each skill's ``triggers`` are matched against the prompt, legacy names
resolve to their replacement, and a few phrase patterns select the execution
mode. The optional live evaluation (``scripts/routing_eval.py --live``) asks a
real model the same questions and compares its answers with this router's.

Scoring is intentionally simple so it stays explainable: every matched
trigger phrase adds its word count (multi-word phrases are more specific),
naming the skill itself is decisive, ties break by visibility rank then name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ml_python_base.skills_sync.catalog import resolve_name
from ml_python_base.skills_sync.models import VISIBILITY_RANK, Skill

if TYPE_CHECKING:
    from ml_python_base.skills_sync.models import Registry

MODE_FULL = "full"
MODE_EXECUTE_ONLY = "execute_only"
MODE_LOCAL_MODEL = "local_model_32k"

_EXPLICIT_NAME_SCORE = 100

_EXECUTE_ONLY_PATTERNS = (
    r"\bapproved plan\b",
    r"\balready approved\b",
    r"\bimplement (?:the|this) (?:approved )?plan\b",
    r"\bexecute (?:the|this) plan\b",
    r"\bplan (?:in|at|from) docs/",
    r"\baccording to the plan\b",
    r"\bfollow(?:ing)? the plan\b",
)
_LOCAL_MODEL_PATTERNS = (
    r"\bsmall model\b",
    r"\blocal model\b",
    r"\bself-hosted\b",
    r"\b32k\b",
    r"\blocal_model_32k\b",
    r"\bLOCAL_AGENT\b",
    r"\bweak model\b",
    r"\bqwen\b",
    r"\blm studio\b",
    r"\bollama\b",
)


@dataclass(frozen=True)
class Decision:
    """The router's answer for one prompt."""

    skill: str | None
    family: str
    mode: str
    score: int
    ranked: tuple[tuple[str, int], ...] = ()
    resolved_from: str = ""
    matched: tuple[str, ...] = field(default=())

    @property
    def ambiguous(self) -> bool:
        """Two live skills tied for the top score."""
        return (
            len(self.ranked) >= 2
            and self.ranked[0][1] == self.ranked[1][1]
            and self.ranked[0][1] > 0
        )

    def as_dict(self) -> dict:
        return {
            "skill": self.skill,
            "family": self.family,
            "mode": self.mode,
            "score": self.score,
            "ambiguous": self.ambiguous,
            "ranked": [list(item) for item in self.ranked],
            "resolved_from": self.resolved_from,
            "matched": list(self.matched),
        }


def detect_mode(prompt: str) -> str:
    """Execution mode hinted by the prompt (independent of the chosen skill)."""
    lowered = prompt.lower()
    if any(re.search(p, prompt, re.IGNORECASE) for p in _LOCAL_MODEL_PATTERNS):
        return MODE_LOCAL_MODEL
    if any(re.search(p, lowered) for p in _EXECUTE_ONLY_PATTERNS):
        return MODE_EXECUTE_ONLY
    return MODE_FULL


def route(prompt: str, skills: list[Skill], registry: Registry) -> Decision:
    """Pick the skill the catalog routes ``prompt`` to."""
    mode = detect_mode(prompt)
    by_name = {skill.name: skill for skill in skills}
    live = [s for s in skills if s.meta.is_discoverable]

    explicit = _explicit_name(prompt, skills, registry)
    if explicit is not None:
        name, resolved_from = explicit
        skill = by_name[name]
        return Decision(
            skill=name,
            family=skill.meta.family,
            mode=mode,
            score=_EXPLICIT_NAME_SCORE,
            ranked=((name, _EXPLICIT_NAME_SCORE),),
            resolved_from=resolved_from,
            matched=(resolved_from or name,),
        )

    scored: list[tuple[Skill, int, tuple[str, ...]]] = []
    for skill in live:
        score, matched = _score(prompt, skill)
        if mode == MODE_LOCAL_MODEL and skill.meta.small_model_path and score:
            score += 1
        if score:
            scored.append((skill, score, matched))
    scored.sort(
        key=lambda item: (
            -item[1],
            VISIBILITY_RANK.get(item[0].meta.visibility, 9),
            item[0].name,
        )
    )
    ranked = tuple((s.name, score) for s, score, _ in scored[:5])
    if not scored:
        return Decision(skill=None, family="", mode=mode, score=0)
    best, best_score, matched = scored[0]
    return Decision(
        skill=best.name,
        family=best.meta.family,
        mode=mode,
        score=best_score,
        ranked=ranked,
        matched=matched,
    )


def _explicit_name(
    prompt: str, skills: list[Skill], registry: Registry
) -> tuple[str, str] | None:
    """A skill (or retired alias) named verbatim in the prompt wins outright."""
    candidates = {skill.name for skill in skills}
    candidates.update(alias.name for alias in registry.catalog.aliases)
    hits = [
        name
        for name in sorted(candidates, key=len, reverse=True)
        if re.search(rf"(?<![\w/-]){re.escape(name)}(?![\w-])", prompt)
    ]
    if not hits:
        return None
    named = hits[0]
    resolved = resolve_name(named, skills, registry)
    live = {
        s.name: s
        for s in skills
        if s.meta.is_discoverable or s.meta.visibility == "hidden"
    }
    if resolved not in live:
        return None
    return resolved, (named if named != resolved else "")


def _score(prompt: str, skill: Skill) -> tuple[int, tuple[str, ...]]:
    score = 0
    matched: list[str] = []
    for phrase in skill.meta.triggers:
        pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?:s|es|ing|ed)?(?!\w)"
        if re.search(pattern, prompt.lower()):
            score += max(1, len(phrase.split()))
            matched.append(phrase)
    return score, tuple(matched)
