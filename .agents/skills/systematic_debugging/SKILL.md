---
name: systematic_debugging
description: Use when diagnosing a bug, failing test, or unexpected behavior — drive a methodical reproduce → isolate → hypothesize → fix → verify loop instead of guessing. Prevents thrashing and repeated edits to the same file.
---

# Skill: systematic_debugging

## Purpose

Find and fix the root cause of a defect through a disciplined loop rather than
trial-and-error edits. Reduces rework and keeps changes minimal and targeted.
This skill is a workflow to follow inline, not an agent to invoke or delegate to.

## Required Input

- A description of the symptom and how it was observed (error, failing test, wrong
  output).
- The command or steps that trigger it, if known.
- Relevant scope: file(s), module, or feature area.

## Output Format

- A minimal reproduction (command or test).
- The identified root cause, stated plainly.
- The smallest fix that addresses the cause (not the symptom).
- Verification evidence: the command run and its result.

## Execution Rules

1. **Ground.** Confirm the actual working root first (`pwd`/`ls`): the directory
   that contains `.git` and the failing test's path (in this template: `Makefile`,
   `pyproject.toml`, `src/`). Pin it and prefix every later path with it. If a
   path errors, do not retry it — re-derive it with one `find <root> -name <file>`
   and use the printed path. Open the failing test plus the implementation it
   exercises from that root, and restate the exact exception type, message,
   operands, and failing call site (file:line) before hypothesizing.
2. **Reproduce first.** Establish a reliable, minimal repro before changing code,
   using the repo's own documented runner (check `Makefile`, `tox.ini`,
   `scripts/`, CONTRIBUTING; here: `make test` / focused `uv run pytest`); else
   `python -m pytest <test> -x`; if pytest is missing, execute the real test
   file's functions directly. Never write a new script that approximates the
   test. If you cannot reproduce it, gather more signal rather than guessing.
3. **Isolate.** Narrow the failure to the smallest scope — bisect, add focused
   assertions, or read the failing path. Form one hypothesis at a time; after two
   probes that fail to confirm it, stop, re-read the evidence, and reframe instead
   of stacking guesses.
4. **Confirm the cause before fixing.** State why the bug happens and back it with
   evidence. Do not edit speculatively.
5. **Fix the cause, minimally.** Avoid broad rewrites. Do not repeatedly hammer the
   same file — if you are on the third edit, step back and re-diagnose. If a patch
   fails to apply, re-read only the ~10 lines around the target, rebuild the old
   text from that exact output, and retry with a smaller hunk — never retry the
   same patch or free-hand the line. Keep edits small and incremental until the
   current failure is verified fixed.
6. **Verify.** After every edit batch, run a fast parse/compile check
   (`python -m py_compile <changed files>`) before any smoke test. Then re-run
   the exact rule-2 repro and the relevant tests via the same runner order —
   done means that rerun passes. After a failed verification, make a new code
   change or take the next diagnostic step; never re-read unchanged code, never
   repeat the same failed command more than twice, and never treat a
   parse/syntax check alone as verification. Add a regression test when
   practical (`test-driven-development`).
7. **Record.** Capture any non-obvious gotcha in `memory/learnings.md`.
8. Comply with governance: `.github/architecture.md`, `.github/standards.md`.
