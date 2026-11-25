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
            unless a reviewer model is given below. Pass model and effort as options of your
            subagent tool. If one is rejected, stop and ask; never substitute another model.

SHIP        Commit on <branch> (commit-style skill if installed). Push only <branch>.
            Open a PR against <base> (pr skill if installed). Never merge, enable auto-merge,
            or force-push.
            <or the narrower rule the user gave: "commit only" / "do not commit">

QUESTIONS   Ask the coordinator with Orca's `ask` command, not a local question tool.

DONE        Leave the worktree clean. Call `worker_done` with
            --report-path <scratch dir>/<unit>.md containing: branch, head SHA, PR URL,
            commands run and results, reviewers used with their models, deviations, blockers.
```

## Simple unit

```
WORKFLOW    Do not load poteto-mode. Make the smallest change that meets ACCEPTANCE, run the
            repository's checks for it, review your own diff, then ship. If the unit needs a
            design choice or more files than FILES, stop and ask the coordinator to re-tier it.
```

## Complex unit

```
WORKFLOW    Read <absolute path to poteto-mode/SKILL.md> in full. Follow its per-unit playbook
            for this task (Feature, Bug fix, or Refactoring), including its prescribed reviews,
            and its Opening a PR playbook. Do not run its Orchestrate or Autopilot playbooks.

REVIEWERS   <review model / effort, one per line>
            These replace poteto's reviewer models (pstack-models.mdc lines and built-in slugs)
            for interrogate adversaries, review panels, arena cross-judges, and fix rechecks.
            Give each panel seat a different model from this list while models remain.
            All other poteto roles, including arena runners, use the MODEL line.

HELPERS     This task asks you to use subagents. Start poteto's helpers, with at most
            <review_budget> reviewer helpers in total, fix rechecks included. When the budget is
            short, merge review axes into one reviewer and report the cut as a deviation.
```
