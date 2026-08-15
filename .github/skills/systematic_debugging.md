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

1. **Ground.** Confirm the actual repository root first (`pwd`/`ls`; look for
   `Makefile`, `pyproject.toml`, `src/`) and open the failing test plus the
   implementation it exercises from that root. Restate the exact exception type,
   message, operands, and failing call site (file:line) before hypothesizing.
2. **Reproduce first.** Establish a reliable, minimal repro before changing code. If
   you cannot reproduce it, gather more signal rather than guessing.
3. **Isolate.** Narrow the failure to the smallest scope — bisect, add focused
   assertions, or read the failing path. Form one hypothesis at a time; after two
   probes that fail to confirm it, stop, re-read the evidence, and reframe instead
   of stacking guesses.
4. **Confirm the cause before fixing.** State why the bug happens and back it with
   evidence. Do not edit speculatively.
5. **Fix the cause, minimally.** Avoid broad rewrites. Do not repeatedly hammer the
   same file — if you are on the third edit, step back and re-diagnose. Keep edits
   small and incremental until the current failure is verified fixed.
6. **Verify.** After every edit batch, run a fast parse/compile check
   (`uv run python -m py_compile <changed files>`) before any smoke test. Then
   re-run the repro and the relevant tests (`make test` / focused `pytest`). If the
   preferred runner is unavailable, immediately fall back to the lightest check
   that executes the code (e.g. an import-and-call one-liner) — do not stop, and
   never treat a parse/syntax check alone as verification. Add a regression test
   when practical (`test-driven-development`).
7. **Record.** Capture any non-obvious gotcha in `memory/learnings.md`.
8. Comply with governance: `.github/architecture.md`, `.github/standards.md`.
