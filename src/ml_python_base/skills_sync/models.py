"""Immutable data models for the skills sync engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Link strategies a tool can use to materialize its native skills view.
LINK_SYMLINK = "symlink"
LINK_COPY = "copy"
LINK_NONE = "none"
VALID_LINK_STRATEGIES = frozenset({LINK_SYMLINK, LINK_COPY, LINK_NONE})

# Skill provenance.
KIND_INTERNAL = "internal"
KIND_EXTERNAL = "external"

# Agent kinds and modes.
AGENT_ORCHESTRATOR = "orchestrator"
AGENT_WORKER = "worker"
MODE_PRIMARY = "primary"
MODE_SUBAGENT = "subagent"

# Native agent projection formats.
AGENT_FORMAT_CLAUDE = "claude"
AGENT_FORMAT_OPENCODE = "opencode"
AGENT_FORMAT_CODEX = "codex"  # TOML, lives at .codex/agents/<name>.toml

# --- Skill catalog metadata ---------------------------------------------------
#
# Visibility says who a skill is for and whether it competes in model discovery:
#
# * ``developer`` — an entrypoint a developer thinks in ("implement a feature").
#   Listed first in every adapter, projected natively.
# * ``internal``  — a primitive the entrypoints compose. Projected natively and
#   listed compactly; invoked directly only when the task *is* that primitive.
# * ``optional``  — a specialist capability behind a profile (python-ml,
#   frontend, ...). Projected natively, listed under its profile.
# * ``hidden``    — available if named explicitly, never listed for discovery.
# * ``legacy``    — a compatibility alias. NOT projected; the adapter maps the old
#   name to its ``replacement``.
VISIBILITY_DEVELOPER = "developer"
VISIBILITY_INTERNAL = "internal"
VISIBILITY_OPTIONAL = "optional"
VISIBILITY_HIDDEN = "hidden"
VISIBILITY_LEGACY = "legacy"
VALID_VISIBILITIES = frozenset(
    {
        VISIBILITY_DEVELOPER,
        VISIBILITY_INTERNAL,
        VISIBILITY_OPTIONAL,
        VISIBILITY_HIDDEN,
        VISIBILITY_LEGACY,
    }
)
# Lower ranks win ties in routing and sort first in listings.
VISIBILITY_RANK = {
    VISIBILITY_DEVELOPER: 0,
    VISIBILITY_INTERNAL: 1,
    VISIBILITY_OPTIONAL: 2,
    VISIBILITY_HIDDEN: 3,
    VISIBILITY_LEGACY: 4,
}

MATURITY_STABLE = "stable"
MATURITY_EXPERIMENTAL = "experimental"
MATURITY_DEPRECATED = "deprecated"
VALID_MATURITIES = frozenset(
    {MATURITY_STABLE, MATURITY_EXPERIMENTAL, MATURITY_DEPRECATED}
)

RISK_READ_ONLY = "read-only"
RISK_WRITES_FILES = "writes-files"
RISK_GIT_MUTATING = "git-mutating"
RISK_NETWORK = "network"
VALID_RISKS = frozenset(
    {RISK_READ_ONLY, RISK_WRITES_FILES, RISK_GIT_MUTATING, RISK_NETWORK}
)

DEFAULT_FAMILY = "unclassified"
DEFAULT_PROFILE = "core"

# How long the one-line summary shown in adapter files may be. Adapter files are
# read by every model, including small self-hosted ones, so the derived summary
# is clipped hard; a skill that needs more sets ``summary`` explicitly.
SUMMARY_MAX_CHARS = 140


@dataclass(frozen=True)
class Policy:
    """A governed policy projected over skills whose source cannot be edited.

    The canonical example is ``git-actions``: vendored skills instruct commits,
    pushes and merges; this repository forbids agents from running them
    unasked. The policy is rendered into every adapter file and, for the skills
    it applies to, into the projected ``SKILL.md`` ahead of the vendor body.
    """

    id: str
    title: str
    summary: str
    applies_to: tuple[str, ...] = ()
    doc: str = ""


@dataclass(frozen=True)
class SkillMeta:
    """Catalog metadata of one skill.

    Authored in the skill's own frontmatter for internal skills and declared as
    a ``[skill.<name>]`` overlay in the registry for vendored ones (the overlay
    wins when both exist). Every field has a default so a skill with no
    metadata at all still projects — as an ``internal`` primitive of family
    ``unclassified``.
    """

    family: str = DEFAULT_FAMILY
    visibility: str = VISIBILITY_INTERNAL
    profile: str = DEFAULT_PROFILE
    auto_trigger: bool = True
    maturity: str = MATURITY_STABLE
    risk: str = RISK_WRITES_FILES
    small_model_path: bool = False
    triggers: tuple[str, ...] = ()
    replacement: str = ""
    summary: str = ""
    policies: tuple[Policy, ...] = ()

    @property
    def is_legacy(self) -> bool:
        return self.visibility == VISIBILITY_LEGACY

    @property
    def is_projected(self) -> bool:
        """Whether native views materialize the skill at all."""
        return not self.is_legacy

    @property
    def is_discoverable(self) -> bool:
        """Whether adapters list the skill for the model to pick from."""
        return self.visibility in (
            VISIBILITY_DEVELOPER,
            VISIBILITY_INTERNAL,
            VISIBILITY_OPTIONAL,
        )


@dataclass(frozen=True)
class Skill:
    """A governed skill discovered from the source of truth.

    Shape and provenance are independent. A skill takes one of two shapes:

    * **flat** — a single ``<name>.md`` file, for a skill that is only prose;
    * **bundle** — a directory whose entry point is ``SKILL.md``, shipping the
      scripts, templates or references the skill runs beside it.

    Internal skills (``.github/skills/``) may use either shape; external skills
    (``.github/skills-external/``) are always bundles. Consumers that care about
    the on-disk layout must branch on :attr:`is_bundle`, never on :attr:`kind`.

    ``description`` is the *effective* trigger text (a registry overlay may
    replace a vendor's); ``source_description`` is what the file on disk says.
    When they differ, or a policy applies, the projected ``SKILL.md`` is a
    generated overlay file rather than a symlink — see :mod:`overlay`.
    """

    name: str
    kind: str  # KIND_INTERNAL | KIND_EXTERNAL
    source_path: Path  # flat `.md` file, or a directory containing SKILL.md
    description: str = ""
    source_description: str = ""
    meta: SkillMeta = field(default_factory=SkillMeta)

    @property
    def is_internal(self) -> bool:
        return self.kind == KIND_INTERNAL

    @property
    def is_bundle(self) -> bool:
        """True when the skill ships helper files next to its ``SKILL.md``."""
        return self.source_path.is_dir()

    @property
    def skill_file(self) -> Path:
        """The markdown entry point, whatever the shape."""
        return self.source_path / "SKILL.md" if self.is_bundle else self.source_path

    @property
    def needs_overlay(self) -> bool:
        """Whether the projected ``SKILL.md`` must be generated, not linked."""
        return bool(self.meta.policies) or (
            bool(self.source_description)
            and self.description != self.source_description
        )

    @property
    def summary(self) -> str:
        """One line for adapter listings: explicit ``summary`` or a clipped trigger."""
        if self.meta.summary:
            return self.meta.summary
        return short_summary(self.description)


def short_summary(text: str, limit: int = SUMMARY_MAX_CHARS) -> str:
    """Clip ``text`` to its first sentence, then to ``limit`` characters.

    Deterministic so the generated adapter files stay stable across runs.
    """
    text = " ".join(text.split())
    if not text:
        return ""
    for separator in (". ", " — ", " - "):
        head, sep, _tail = text.partition(separator)
        if sep and len(head) >= 24:
            text = head.rstrip(".")
            break
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rsplit(" ", 1)[0]
    return clipped.rstrip(",;:") + "…"


@dataclass(frozen=True)
class Alias:
    """A retired skill name that still resolves to a live skill."""

    name: str
    replacement: str
    note: str = ""


@dataclass(frozen=True)
class Intent:
    """One row of the human-facing 'I want to… → use' table."""

    want: str
    skill: str
    note: str = ""


@dataclass(frozen=True)
class CatalogSpec:
    """The ``[catalog]`` / ``[skill.*]`` / ``[alias.*]`` / ``[policy.*]`` blocks."""

    families: tuple[str, ...] = ()
    profiles: tuple[str, ...] = ()
    output: str = ""  # repo-relative path of the generated catalog document
    routing_rules: tuple[str, ...] = ()
    small_model_note: str = ""
    overlays: dict[str, dict] = field(default_factory=dict)
    aliases: tuple[Alias, ...] = ()
    policies: tuple[Policy, ...] = ()
    intents: tuple[Intent, ...] = ()

    def policies_for(self, skill_name: str) -> tuple[Policy, ...]:
        return tuple(p for p in self.policies if skill_name in p.applies_to)

    def alias(self, name: str) -> Alias | None:
        for alias in self.aliases:
            if alias.name == name:
                return alias
        return None


@dataclass(frozen=True)
class ToolSpec:
    """One AI tool that consumes governed skills, declared in the registry."""

    id: str
    display_name: str
    link_strategy: str
    native_skills_dir: str = ""
    needs_manifest: bool = False
    manifest_path: str | None = None
    adapter_file: str | None = None
    adapter_template: str | None = None
    reference_prefix: str = ""
    adapter_frontmatter: str | None = None
    native_agents_dir: str = ""
    agent_format: str = ""

    @property
    def has_native_view(self) -> bool:
        return bool(self.native_skills_dir) and self.link_strategy != LINK_NONE

    @property
    def has_agent_view(self) -> bool:
        return bool(self.native_agents_dir) and bool(self.agent_format)


@dataclass(frozen=True)
class Agent:
    """A governed, tool-agnostic agent definition from ``.github/agents``."""

    name: str
    description: str
    kind: str  # AGENT_ORCHESTRATOR | AGENT_WORKER
    mode: str  # MODE_PRIMARY | MODE_SUBAGENT
    tier: str  # planner | executor | fast
    allowed_tools: tuple[str, ...]
    governance: tuple[str, ...]
    skills: tuple[str, ...]
    delegates_to: tuple[str, ...]
    context_budget: str
    body: str

    @property
    def is_orchestrator(self) -> bool:
        return self.kind == AGENT_ORCHESTRATOR


@dataclass(frozen=True)
class Governance:
    """Governance files surfaced in every generated adapter region."""

    files: tuple[str, ...]
    automation: str
    orchestration: str


@dataclass(frozen=True)
class TemplateSyncPolicy:
    """Versioned ownership boundary for downstream template synchronization.

    Protocol ``0`` represents a legacy registry without explicit lifecycle
    metadata. Governance paths may be applied selectively; platform paths are
    inventory only and always require a separate, manually reviewed upgrade.
    """

    protocol: int = 0
    governance_paths: tuple[str, ...] = ()
    platform_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Registry:
    """The parsed declarative registry."""

    schema_version: int
    governance: Governance
    tools: tuple[ToolSpec, ...]
    template_sync: TemplateSyncPolicy = field(default_factory=TemplateSyncPolicy)
    catalog: CatalogSpec = field(default_factory=CatalogSpec)

    def tool(self, tool_id: str) -> ToolSpec:
        for spec in self.tools:
            if spec.id == tool_id:
                return spec
        raise KeyError(tool_id)
