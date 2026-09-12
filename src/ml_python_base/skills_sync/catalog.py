"""Catalog metadata: merge, validate, and partition skills for adapters.

The catalog is the layer between raw discovery (files on disk) and projection
(what each tool sees). It answers three questions the flat skill list could
not: *who is this skill for* (visibility), *what is it about* (family,
profile) and *what happens to the old name* (aliases, replacements).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

from ml_python_base.skills_sync.errors import RegistryError
from ml_python_base.skills_sync.frontmatter import as_bool, as_str_tuple
from ml_python_base.skills_sync.models import (
    DEFAULT_FAMILY,
    MATURITY_DEPRECATED,
    VALID_MATURITIES,
    VALID_RISKS,
    VALID_VISIBILITIES,
    VISIBILITY_DEVELOPER,
    VISIBILITY_HIDDEN,
    VISIBILITY_INTERNAL,
    VISIBILITY_LEGACY,
    VISIBILITY_OPTIONAL,
    VISIBILITY_RANK,
    Alias,
    Skill,
    SkillMeta,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ml_python_base.skills_sync.models import Registry

# Keys a skill may declare (frontmatter) or a registry overlay may set.
META_KEYS = frozenset(
    {
        "family",
        "visibility",
        "profile",
        "auto_trigger",
        "maturity",
        "risk",
        "small_model_path",
        "triggers",
        "replacement",
        "summary",
    }
)
# Overlay-only key: replaces the vendor's trigger text in the projected view.
OVERLAY_DESCRIPTION_KEY = "description"


def meta_from_mapping(
    data: Mapping[str, Any], base: SkillMeta | None = None
) -> SkillMeta:
    """Build metadata from frontmatter or an overlay, on top of ``base``."""
    base = base or SkillMeta()
    updates: dict[str, Any] = {}
    for key in ("family", "visibility", "profile", "maturity", "risk", "replacement"):
        if key in data and str(data[key]).strip():
            updates[key] = str(data[key]).strip()
    if "summary" in data:
        updates["summary"] = " ".join(str(data["summary"]).split())
    if "auto_trigger" in data:
        updates["auto_trigger"] = as_bool(data["auto_trigger"], base.auto_trigger)
    if "small_model_path" in data:
        updates["small_model_path"] = as_bool(
            data["small_model_path"], base.small_model_path
        )
    if "triggers" in data:
        updates["triggers"] = as_str_tuple(data["triggers"])
    return replace(base, **updates)


def apply_registry(skills: list[Skill], registry: Registry) -> list[Skill]:
    """Merge registry overlays and policies into each discovered skill.

    Precedence per field: registry overlay > frontmatter > defaults. Policies
    are attached from ``[policy.*].applies_to`` so a projected skill carries
    everything the linker needs without consulting the registry again.
    """
    spec = registry.catalog
    merged: list[Skill] = []
    for skill in skills:
        overlay = spec.overlays.get(skill.name, {})
        meta = meta_from_mapping(overlay, base=skill.meta)
        meta = replace(meta, policies=spec.policies_for(skill.name))
        alias = spec.alias(skill.name)
        if alias is not None:
            # The registry says this name is retired. A downstream tree that still
            # carries the directory (governance sync overlays files, it does not
            # delete them) projects it as legacy instead of resurrecting it.
            meta = replace(
                meta,
                visibility=VISIBILITY_LEGACY,
                maturity=MATURITY_DEPRECATED,
                replacement=alias.replacement,
                summary=alias.note or meta.summary,
            )
        description = skill.source_description or skill.description
        override = str(overlay.get(OVERLAY_DESCRIPTION_KEY, "")).strip()
        if override:
            description = " ".join(override.split())
        merged.append(replace(skill, description=description, meta=meta))
    return merged


def validate_catalog(skills: list[Skill], registry: Registry) -> list[str]:
    """Return every hard catalog inconsistency as a human-readable message.

    Hard problems are contradictions among the skills that *are* present or
    invalid vocabulary. References to skills that are absent from this tree
    (an overlay, policy, intent or alias pointing at a purged or not-yet-synced
    skill) are reported by :func:`catalog_warnings` instead, so a downstream
    repository that carries a subset of the catalog still syncs.
    """
    spec = registry.catalog
    by_name = {skill.name: skill for skill in skills}
    problems: list[str] = []

    for name in sorted(spec.overlays):
        unknown = sorted(
            set(spec.overlays[name]) - META_KEYS - {OVERLAY_DESCRIPTION_KEY}
        )
        if unknown:
            problems.append(f"[skill.{name}] has unknown keys: {', '.join(unknown)}")

    for skill in skills:
        problems.extend(_validate_skill(skill, by_name, registry))

    for alias in spec.aliases:
        target = by_name.get(alias.replacement)
        if target is not None and target.meta.is_legacy:
            problems.append(
                f"[alias.{alias.name}] replacement '{alias.replacement}' is legacy"
            )

    for intent in spec.intents:
        target = by_name.get(intent.skill)
        if target is not None and not target.meta.is_discoverable:
            problems.append(
                f"intent '{intent.want}' points at non-discoverable skill "
                f"'{intent.skill}'"
            )
    return problems


def catalog_warnings(skills: list[Skill], registry: Registry) -> list[str]:
    """Dangling references: catalog entries naming skills absent from this tree."""
    spec = registry.catalog
    present = {skill.name for skill in skills}
    warnings: list[str] = []
    for name in sorted(spec.overlays):
        if name not in present:
            warnings.append(f"[skill.{name}] overlays a skill that is not present")
    for alias in spec.aliases:
        if alias.name in present:
            warnings.append(
                f"[alias.{alias.name}] shadows a skill still on disk; it is "
                f"projected as legacy — delete its directory to finish retiring it"
            )
    for alias in spec.aliases:
        if alias.replacement not in present:
            warnings.append(
                f"[alias.{alias.name}] replacement '{alias.replacement}' is not present"
            )
    for policy in spec.policies:
        for name in policy.applies_to:
            if name not in present:
                warnings.append(
                    f"[policy.{policy.id}] applies to absent skill '{name}'"
                )
    for intent in spec.intents:
        if intent.skill not in present:
            warnings.append(
                f"intent '{intent.want}' points at absent skill '{intent.skill}'"
            )
    return warnings


def _validate_skill(
    skill: Skill, by_name: Mapping[str, Skill], registry: Registry
) -> list[str]:
    spec = registry.catalog
    meta = skill.meta
    problems: list[str] = []
    prefix = f"skill '{skill.name}'"
    if meta.visibility not in VALID_VISIBILITIES:
        problems.append(f"{prefix}: invalid visibility '{meta.visibility}'")
    if meta.maturity not in VALID_MATURITIES:
        problems.append(f"{prefix}: invalid maturity '{meta.maturity}'")
    if meta.risk not in VALID_RISKS:
        problems.append(f"{prefix}: invalid risk '{meta.risk}'")
    if (
        spec.families
        and meta.family != DEFAULT_FAMILY
        and meta.family not in spec.families
    ):
        problems.append(f"{prefix}: family '{meta.family}' not in [catalog].families")
    if spec.profiles and meta.profile not in spec.profiles:
        problems.append(f"{prefix}: profile '{meta.profile}' not in [catalog].profiles")
    if meta.maturity == MATURITY_DEPRECATED and not meta.is_legacy:
        problems.append(f"{prefix}: deprecated skills must have visibility 'legacy'")
    if meta.is_legacy:
        target = by_name.get(meta.replacement)
        if not meta.replacement or (target is not None and target.meta.is_legacy):
            problems.append(f"{prefix}: legacy skill needs a live 'replacement'")
    return problems


def assert_valid_catalog(skills: list[Skill], registry: Registry) -> None:
    problems = validate_catalog(skills, registry)
    if problems:
        joined = "\n".join(f"  - {problem}" for problem in problems)
        raise RegistryError(f"Skill catalog is inconsistent:\n{joined}")


@dataclass(frozen=True)
class CatalogView:
    """Skills partitioned the way adapters and the catalog document show them."""

    entrypoints: tuple[Skill, ...] = ()
    primitives: tuple[Skill, ...] = ()
    optional: tuple[Skill, ...] = ()
    hidden: tuple[Skill, ...] = ()
    legacy: tuple[Skill, ...] = ()
    aliases: tuple[Alias, ...] = ()
    small_model: tuple[Skill, ...] = ()
    families: tuple[tuple[str, tuple[Skill, ...]], ...] = ()
    profiles: tuple[tuple[str, tuple[Skill, ...]], ...] = field(default=())

    @property
    def discoverable(self) -> tuple[Skill, ...]:
        return self.entrypoints + self.primitives + self.optional


def build_view(skills: list[Skill], registry: Registry) -> CatalogView:
    """Partition ``skills`` deterministically (visibility rank, then name)."""
    ordered = sorted(
        skills, key=lambda s: (VISIBILITY_RANK.get(s.meta.visibility, 9), s.name)
    )
    bucket: dict[str, list[Skill]] = {
        VISIBILITY_DEVELOPER: [],
        VISIBILITY_INTERNAL: [],
        VISIBILITY_OPTIONAL: [],
        VISIBILITY_HIDDEN: [],
    }
    legacy: list[Skill] = []
    for skill in ordered:
        if skill.meta.is_legacy:
            legacy.append(skill)
        else:
            bucket.setdefault(skill.meta.visibility, []).append(skill)

    declared = {alias.name for alias in registry.catalog.aliases}
    aliases = [
        Alias(name=s.name, replacement=s.meta.replacement, note=s.summary)
        for s in legacy
        if s.name not in declared
    ] + list(registry.catalog.aliases)
    aliases.sort(key=lambda a: a.name)

    live = [s for s in ordered if not s.meta.is_legacy]
    families = _group(live, lambda s: s.meta.family, registry.catalog.families)
    profiles = _group(live, lambda s: s.meta.profile, registry.catalog.profiles)
    return CatalogView(
        entrypoints=tuple(bucket[VISIBILITY_DEVELOPER]),
        primitives=tuple(bucket[VISIBILITY_INTERNAL]),
        optional=tuple(bucket[VISIBILITY_OPTIONAL]),
        hidden=tuple(bucket[VISIBILITY_HIDDEN]),
        legacy=tuple(legacy),
        aliases=tuple(aliases),
        small_model=tuple(s for s in live if s.meta.small_model_path),
        families=families,
        profiles=profiles,
    )


def _group(
    skills: list[Skill], key: Any, declared: tuple[str, ...]
) -> tuple[tuple[str, tuple[Skill, ...]], ...]:
    names = list(declared) + sorted({key(s) for s in skills} - set(declared))
    groups = []
    for name in names:
        members = tuple(s for s in skills if key(s) == name)
        if members:
            groups.append((name, members))
    return tuple(groups)


def resolve_name(name: str, skills: list[Skill], registry: Registry) -> str:
    """Map a possibly retired skill name to the live skill that replaces it."""
    by_name = {skill.name: skill for skill in skills}
    seen: set[str] = set()
    current = name
    while current not in seen:
        seen.add(current)
        skill = by_name.get(current)
        if skill is not None and not skill.meta.is_legacy:
            return current
        if skill is not None:
            current = skill.meta.replacement
            continue
        alias = registry.catalog.alias(current)
        if alias is None:
            return current
        current = alias.replacement
    return current
