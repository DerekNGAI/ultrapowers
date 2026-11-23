# Orca worker contract

Apply this contract only to the `orca-poteto` unit in your brief. Your brief's `TIER` picks your workflow: `standard` runs without poteto, and `complex` runs poteto-mode. Keep the installed skills and shared settings unchanged.

## Standard workers

Do not load poteto-mode.

1. Read the brief's Ownership files and acceptance, and the code they touch.
2. Make the smallest change that meets acceptance within the brief's constraints.
3. Run the repository's checks for the code you touched, such as its tests, linter, and type checker. Fix the failures your change causes.
4. Review your own `git diff` against acceptance and constraints, and fix what you find.
5. Ship the unit per [Ship](#ship).

You may run read-only helpers in parallel through your native subagent tool, on your `implementation` entry, per [Helpers](#helpers). Do not start reviewer helpers.

If the unit needs a design decision the brief does not settle, or is much larger than the brief describes, stop before expanding scope and `ask` the coordinator to re-tier it.

## Complex workers

Load the installed `poteto-mode/SKILL.md` from the brief's `SKILLS` path in this worker session.

Select the per-unit poteto playbook or review skill for your assigned role, then load its routed skills as needed. Own the unit's design, implementation, verification, prescribed reviews, commits, and PR description within the brief's scope and permissions. Review workers return findings. Implementation workers make fixes.

Use poteto's per-unit playbooks, such as Feature, Bug fix, and Refactoring. Route project-level work to the coordinator. Do not run poteto's Orchestrate, Autopilot-full, or Autopilot-stack playbooks, or its `scripts/orch` store.

Include review findings and their resolution in the completion evidence so the coordinator can check acceptance without repeating your workflow.

### Review budget

`REVIEW_BUDGET` caps the reviewer helpers you start for this unit across its whole workflow, fix rechecks included. A reviewer is any helper that returns findings or a verdict on the unit's work. Sketchers, explainers, and other helpers that produce material do not count. With `REVIEW_BUDGET: default`, keep each routed skill's reviewer count.

When the routed skills prescribe more reviewers than the budget allows, combine them. A combined reviewer receives every merged axis's brief and reports findings per axis. Combine panel members that share a review entry first, since repeating one model adds little independence. Spread reviewers across the `review` entries, and give each member of a multi-model panel a distinct entry while entries remain.

If a review is still prescribed after the budget is spent, run that check yourself and report the missing independent review as a deviation.

## Workspace boundaries

Before the first write, verify the actual Git root and branch for every writable repository against the brief's `WORKSPACES` mapping. Each concurrent writer, worker or editing helper, needs its own coordinator-assigned Orca-managed worktree and branch. For a new-worktree creation target, resolve and report the actual path and branch, and verify isolation from the coordinator and other active writers before editing. If placement is missing, mismatched, or shared with another writer, stop before writing and ask the coordinator to resolve it.

Edit only the assigned checkouts. A worktree for one repository does not isolate sibling repositories in the project folder. Read-only workers and helpers may share a checkout while remaining read-only. You may hand your worktree to one editing helper at a time and make no writes until it returns. Ask the coordinator to place concurrent editing helpers in their own worktrees.

## Coordination

Orca's coordinator owns units, task dependencies, and long-lived worker sessions through orchestration.

Ask questions with the `ask` command from your Orca preamble. In a complex unit, poteto's question rules decide whether a question is worth asking. Use that coordinator channel instead of a local question tool.

## Helpers

Spawn short-lived helpers with your native subagent tool, in parallel when they are independent. Complex workers use poteto's engineering helpers, such as `interrogate`, `architect`, or `swarm` verification. Run each on its role's resolved entry in `MODEL_POLICY`, passing the model and effort as the tool's options. Record what you requested for each helper; that record is the evidence for local helpers. A local helper counts as unavailable under Models only when your subagent tool rejects its model or effort. The helper's runtime is your own runtime, since a model option does not change it.

Ask the coordinator to dispatch a helper through Orca only when:

- its entry's agent differs from your runtime and your subagent tool cannot run that agent, or
- it edits files concurrently with you or another helper, per Workspace boundaries.

Keep every other helper in your session. You retain ownership of the workflow either way. Start no Orca workers yourself.

## Models

Use the brief's resolved `MODEL_POLICY` for your role and every helper. It includes the implementation entry and every review entry, and overrides pstack's model choices and automatic effort adjustments for this run.

Use the resolved choices instead of loading another copy of `models.yaml` or resolving model names again. If a selection becomes unavailable or unverifiable, stop that unit and report the problem through the coordinator. Never silently substitute an agent, model, or effort.

## Permissions

- A missing or unclear `PERMISSIONS` line means no.
- A grant covers only the named branch or base, and only the files in the brief's Ownership.
- The coordinator grants only what the user granted to it. It cannot grant merge.
- In a complex unit, the brief's permissions override poteto's Autonomy section for git and forge actions. Poteto's Always-pause list still applies.
- Never, under any grant: merge, enable auto-merge, force-push, retarget an existing PR, or rebase a branch that another agent uses.
- With `commit: yes`, use the installed `commit-style` skill when available, and poteto's commit rules in a complex unit. With `pr: yes` in a complex unit, poteto's Opening a PR playbook applies. Post the PR URL and finish the unit without babysitting or shipping.
- If the work needs a permission the brief does not grant, stop at the last allowed step and `ask` the coordinator. The coordinator asks the user.

## Ship

Take each step your `PERMISSIONS` grant, in order, and stop at the first one they do not:

1. **Commit** the deliverable on your assigned branch.
2. **Push** only that branch with `git push -u origin <branch>`, so the coordinator can delete the local copy after the run.
3. **Open the PR** against the granted base with `gh pr create --base <base> --head <branch>`, writing the body with the installed `pr` skill when available. Complex units use poteto's Opening a PR playbook.

If the push or PR step fails, for example because there is no push remote or `gh` is not authenticated, keep the commit, report the step as blocked, and finish.

## Completion

Leave every assigned checkout clean, because the coordinator removes a clean worktree when the run ends and keeps a dirty one. With `commit: yes`, commit the deliverable and delete the scratch files you created. With `commit: no`, the uncommitted diff is the deliverable: leave it in place and say so in the report.

Report completion once with `worker_done`. Write your full reply to the brief's `REPORT` path, outside every checkout, and pass it as `--report-path`.

Include the actual Git root, branch, pushed head SHA, and `git status --porcelain` output for every assigned checkout, PR URL if any, verification commands and results, verdict, deviations, review evidence, and remaining blockers. Report the requested and effective agent, model, and effort, including inherited fields or unavailable status. In a complex unit, list the reviewer helpers used against `REVIEW_BUDGET` with each one's model, and any helper the coordinator dispatched for you.
