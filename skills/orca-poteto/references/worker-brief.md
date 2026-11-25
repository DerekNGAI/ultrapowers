# Worker brief

Copy this template, replace every `<...>`, and pass it to `worker-start --spec-file`. It is the worker's whole instruction set.

```
TASK        <goal in one paragraph, plus constraints from the request>

FILES       <files or areas this unit owns>

ACCEPTANCE  <observable checks that prove the task is done>

WORKTREE    <worktree path, or "the new worktree Orca created for you">, branch <branch>.
            Before the first edit, confirm `git rev-parse --show-toplevel` and the branch match.
            Edit nothing outside this worktree.

POTETO      Read <absolute path to poteto-mode/SKILL.md> in full. Follow its per-unit playbook
            for this task (Feature, Bug fix, or Refactoring), including its prescribed reviews.
            Do not run its Orchestrate or Autopilot playbooks.

MODELS      You run on <agent> / <model> / <effort>.
            Implementation helpers: <model> / <effort>.
            Reviewer helpers: <review model / effort, one per line>. Spread reviewers across them.
            Pass model and effort as options of your subagent tool. If one is rejected, stop and
            ask; never substitute another model.

HELPERS     This task asks you to use subagents. Run poteto's reviewers as helpers, at most
            <review_budget> in total including fix rechecks. Merge review axes into one reviewer
            when the budget is short.

SHIP        Commit on <branch> (commit-style skill if installed). Push only <branch>.
            Open a PR against <base>. Never merge, enable auto-merge, or force-push.
            <or the narrower rule the user gave: "commit only" / "do not commit">

QUESTIONS   Ask the coordinator with Orca's `ask` command, not a local question tool.

DONE        Leave the worktree clean. Call `worker_done` with
            --report-path <scratch dir>/<unit>.md containing: branch, head SHA, PR URL,
            commands run and results, reviewers used with their models, deviations, blockers.
```
