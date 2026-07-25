# Orchestration Policy

This file defines Level 4 orchestration so complex tasks follow deterministic execution flow.

## Plan-First Requirement

- For non-trivial engineering tasks, create an explicit plan before writing code.
- The plan must include ordered steps, expected outputs, and validation checkpoints.

## Step-by-Step Execution

- Execute work in explicit phases.
- Complete each phase before moving to the next one.
- Re-scope only when a blocking constraint is discovered.
- Size each step to the executor model tier; for weak/self-hosted executors,
  prefer one-file, independently-verifiable steps and a runnable milestone first.
  See `docs/task-sizing.md`.

## Mandatory Diff Review

- Review generated diffs before finalizing.
- Check for unrelated file churn and architectural boundary violations.
- Confirm naming, comments, and docs remain in English.

## Automation Validation

- Validate results against `.github/automation.md` requirements.
- Prefer project command sequence for quality gates:
  - `make format`
  - `make fix`
  - `make lint`
  - `make test`

## Skill Invocation Rule

- Do not perform direct large-scale generation when an internal skill applies.
- Select and invoke relevant skill(s) from `.github/skills/` first.
- Use external synced skills only when no internal skill covers the capability.

## Subagent Handoff Contract

When the orchestrator delegates to a subagent, a complete handoff is a closed loop of
four steps — not a task marked in a tracker:

1. **Bound** — choose one discrete subproblem with an explicit scope and acceptance
   condition. "Everything left" is not a subproblem.
2. **Delegate** — dispatch it to a subagent with the context it needs; the subagent
   does not inherit the orchestrator's history.
3. **Receive** — wait for an explicit, inspectable result (a diff, a decision, a test
   outcome). No advancing on a launched-but-unfinished delegation.
4. **Merge** — incorporate that result into the main plan (update the plan position,
   fold in the produced files or decision) **before** the next subproblem starts.

Task-create / task-update activity is **bookkeeping, not delegation**. A run that
records task motion without a received result and a visible merge step has not
orchestrated anything and must not report progress as if it had.

- **Counts as a handoff:** "Delegated `parser.py` extraction to a subagent → received a
  diff with 3 passing tests → merged it; plan now at step 4/7."
- **Does NOT count:** "Marked task 'refactor parser' in progress" with no dispatched
  subagent, no returned result, and no merge — this is empty orchestration.

On a runtime without real sub-agent delegation, the orchestrator runs the subproblem
itself and still performs the receive/merge steps explicitly (state the result, then
fold it into the plan) so the trace shows a real delegate-and-merge loop, not motion.

## Resumable Execution & Checkpointing

Long, multi-phase runs must preserve confirmed progress across a session or transport
drop — a connection closed mid-response must not discard milestones that already
passed their gate.

- **Checkpoint after every verified milestone or phase.** Record the completed
  milestone, the current plan position (e.g. "step 4/7"), and the completion markers
  (gates that went green). This is part of the normal step, not an extra.
- **Resume from the last confirmed checkpoint**, never from zero and never by assuming
  completion. On re-entry, re-read the plan, find the last checkpoint whose gate was
  green, and continue from the next step.
- **A checkpoint is only valid once its gate is green.** Do not checkpoint a phase whose
  exit gate (`.github/sdlc.md`) has not passed; an ungated checkpoint would resume into
  unverified state.
- **Progress not checkpointed is progress that can be lost.** If a milestone completed
  but was never recorded, treat it as unconfirmed on resume and re-verify it.
