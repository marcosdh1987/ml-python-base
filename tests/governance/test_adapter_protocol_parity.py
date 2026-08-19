"""Guard the hand-written adapter-prose convention mechanically.

The ``## Debugging protocol`` block (and the ``## Working loop`` paragraph) is
maintained as byte-identical copies in ``OPENCODE.md`` and ``AGENTS.md`` so that
weak build models see the same front-loaded rules in every harness. The copies
live outside the machine-owned skills region, so ``make check-sync`` cannot
catch drift between them — this test does.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_FILES = ("OPENCODE.md", "AGENTS.md")
SHARED_SECTIONS = ("## Working loop", "## Debugging protocol")


def extract_section(text: str, heading: str, source: str) -> str:
    pattern = rf"(?ms)^{re.escape(heading)}$\n(.*?)(?=^## )"
    match = re.search(pattern, text)
    assert match, f"{source} is missing the '{heading}' section"
    return match.group(1)


@pytest.mark.parametrize("heading", SHARED_SECTIONS)
def test_shared_adapter_sections_are_byte_identical(heading: str) -> None:
    sections = {
        name: extract_section(
            (REPO_ROOT / name).read_text(encoding="utf-8"), heading, name
        )
        for name in ADAPTER_FILES
    }
    reference_name, *other_names = ADAPTER_FILES
    for name in other_names:
        assert sections[name] == sections[reference_name], (
            f"'{heading}' has drifted between {reference_name} and {name}; "
            "keep the copies byte-identical (see memory/learnings.md)"
        )
