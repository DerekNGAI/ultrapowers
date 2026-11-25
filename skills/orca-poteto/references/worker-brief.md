# Worker brief

Copy the common fields, add the fields for the unit's tier, replace every `<...>`, and pass the result to `worker-start --spec-file`. It is the worker's whole instruction set.

## Common fields

```
TASK        <goal in one paragraph, plus constraints from the request>

FILES       <files or areas this unit owns>

ACCEPTANCE  <observable checks that prove the task is done>

WORKTREE    <worktree path, or "the new worktree Orca created for you">, branch <branch>.
            Before the first edit, confirm `git rev-parse --show-toplevel` and the branch match.
            Edit nothing outside this worktree.

MODEL       You run on <agent> / <model> / <effort>. Any helper you start uses <model> / <effort>
            unless the PSTACK MODELS lines below give its role another model. Pass model and
            effort as options of your subagent tool. If one is rejected, stop and ask; never
            substitute another model.

SHIP        Commit on <branch> (commit-style skill if installed). Push only <branch>.
            Open a PR against <base> (pr skill if installed). Never merge, enable auto-merge,
            or force-push.
            <or the narrower rule the user gave: "commit only" / "do not commit">

QUESTIONS   Ask the coordinator with Orca's `ask` command, not a local question tool.

DONE        Leave the worktree clean. Call `worker_done` with
            --report-path <scratch dir>/<unit>.md containing: branch, head SHA, PR URL,
            commands run and results, helpers used with their roles and models, deviations, blockers.
```

## Simple unit

```
WORKFLOW    Do not load poteto-mode. Make the smallest change that meets ACCEPTANCE, run the
            repository's checks for it, review your own diff, then ship. If the unit needs a
            design choice or more files than FILES, stop and ask the coordinator to re-tier it.
```

## Complex unit

```
WORKFLOW    Read <absolute path to poteto-mode/SKILL.md> in full and follow it: pick the playbook
            that matches this task and run it as written, through its Opening a PR playbook.
            Orca coordinates units, so do not run its Autopilot-full or Autopilot-stack playbooks.

PSTACK MODELS
            These are your pstack-models.mdc lines for this run. They override poteto's role
            defaults and any pstack-models.mdc file.
            <the unit's poteto role lines from model-picker>

SUBAGENTS   This task asks you to use subagents. Start poteto's helpers wherever its playbooks
            call for them.
```
