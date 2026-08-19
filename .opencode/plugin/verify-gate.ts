/**
 * verify-gate — harness-level enforcement for this repository.
 *
 * Why this exists: an unattended "build" pass can ship code that never ran
 * (typos, undefined names, imports to non-existent modules, hallucinated APIs)
 * because the model never executed or verified anything. Governance text alone
 * ("verify with make check") is advisory; a weak/self-hosted build model will
 * skip it. This plugin makes verification mechanical instead of optional.
 *
 * Two layers, both using only verified opencode plugin APIs:
 *
 *   1. tool.execute.after — after every edit/write of a *.py file, auto-fix with
 *      ruff (safe fixes + format) and then surface any remaining ruff / compile
 *      errors back into the tool result. The model sees its own breakage in the
 *      SAME turn, so mechanical bugs cannot silently survive to the end.
 *
 *   2. event:"session.idle" — when the agent finishes a turn, run the full
 *      read-only gate (`make check`) and toast PASS/FAIL. `make check` also
 *      rebuilds .venv from uv.lock, so a red gate also flags undeclared deps.
 *
 * Foreign-workspace degradation: this harness config is also mounted for bench
 * runs whose working directory is a foreign subject repo (no uv.lock, no
 * template Makefile). There, uv/ruff/make either do not exist or — worse —
 * `make check` would run the SUBJECT repo's Makefile. So both layers self-detect
 * the template (uv.lock + pyproject.toml at the root); outside it, layer 1 only
 * parse-checks the edited file with plain python and layer 2 is disabled.
 * Interpreter-missing noise (exit 127 "command not found") is never surfaced —
 * a missing tool is not a code error and must not be reported as one.
 *
 * `import type` is erased at runtime, so this file has no runtime dependency on
 * the (gitignored) @opencode-ai/plugin package.
 */
import { existsSync } from "node:fs";
import type { Plugin } from "@opencode-ai/plugin";

const PYTHON_FILE = /\.py$/;
const EDIT_TOOLS = new Set(["edit", "write"]);
const COMMAND_NOT_FOUND = 127;

export const VerifyGate: Plugin = async ({ $, client, directory }) => {
  const run = (cmd: ReturnType<typeof $>) => cmd.cwd(directory).quiet().nothrow();
  const isTemplate =
    existsSync(`${directory}/uv.lock`) && existsSync(`${directory}/pyproject.toml`);

  return {
    // Layer 1: deterministic auto-fix + same-turn error surfacing for Python.
    "tool.execute.after": async (input, output) => {
      if (!EDIT_TOOLS.has(input.tool)) return;
      const filePath = input.args?.filePath;
      if (typeof filePath !== "string" || !PYTHON_FILE.test(filePath)) return;

      const problems: string[] = [];

      if (isTemplate) {
        // Apply only safe autofixes + formatting (never --unsafe-fixes here).
        await run($`uv run ruff check --fix ${filePath}`);
        await run($`uv run ruff format ${filePath}`);

        // Report what autofix could not resolve (undefined names, bad imports,
        // syntax errors) so the model corrects it immediately.
        const lint = await run($`uv run ruff check ${filePath}`);
        const compile = await run($`uv run python -m py_compile ${filePath}`);

        if (compile.exitCode !== 0) {
          problems.push("py_compile:\n" + compile.stderr.toString().trim());
        }
        if (lint.exitCode !== 0) {
          problems.push("ruff:\n" + lint.stdout.toString().trim());
        }
      } else {
        // Foreign workspace: never reformat a subject repo (it can corrupt the
        // expected patch); parse-check only, with plain python.
        let compile = await run($`python3 -m py_compile ${filePath}`);
        if (compile.exitCode === COMMAND_NOT_FOUND) {
          compile = await run($`python -m py_compile ${filePath}`);
        }
        if (compile.exitCode !== 0 && compile.exitCode !== COMMAND_NOT_FOUND) {
          problems.push("py_compile:\n" + compile.stderr.toString().trim());
        }
      }

      if (problems.length > 0) {
        output.output +=
          `\n\n[verify-gate] ${filePath} still has issues after autofix. ` +
          `Fix these before continuing — do not move on:\n` +
          problems.join("\n");
      }
    },

    // Layer 2: end-of-turn quality gate. A red gate means "not done".
    // Template-only: never run a foreign subject repo's Makefile.
    event: async ({ event }) => {
      if (event.type !== "session.idle") return;
      if (!isTemplate) return;
      const gate = await run($`make check`);
      const passed = gate.exitCode === 0;
      try {
        await client.tui.showToast({
          body: {
            title: "verify-gate",
            message: passed
              ? "make check passed ✅"
              : "make check FAILED ❌ — the work is not done until this is green",
            variant: passed ? "success" : "error",
            duration: 6000,
          },
        });
      } catch {
        // TUI not attached (headless run): the gate still ran; ignore toast.
      }
    },
  };
};
