---
name: orca-poteto
description: Run every implementation task through Orca. Size each unit, do trivial units directly, give standard units to plain Orca workers and complex units to poteto-mode workers, run independent units in parallel, ship each unit as a pull request, then clean up local workspaces. Use whenever asked to implement, build, fix, refactor, or change code, including multi-unit or parallel work, and for /orca-poteto.
---

# Orca + poteto

Every implementation task runs through this skill. This session is the **coordinator**: it splits the request into units, picks a tier for each, dispatches them, accepts the results, ships each unit as a pull request, and cleans up. Poteto-mode runs only inside complex units. These rules apply only to this run and its workers. Leave the installed `orchestration`, `poteto-mode`, and `model-picker` skills and their standalone settings unchanged.

- **Coordinator.** Load the installed `orchestration` skill, resolve its executable, then run `ORCA skills get orchestration`. Follow that version-matched guide and this skill. When a run has a complex unit, locate the installed `poteto-mode/SKILL.md` without loading its contents or routed skills into the coordinator session.
- **Workers.** Start separate sessions with bounded task briefs and the needed file pointers. Pass the [worker contract](references/worker-contract.md) and, for complex units, the absolute poteto skill path in the brief instead of the coordinator's full transcript or this guide.

Status: a recommended adaptation with limited run testing. If a rule here contradicts the current behavior of an underlying skill, stop and report the conflict to the user. Do not improvise a merge.

## Routing

Split the request into **units**. A unit is one deliverable that makes sense on its own branch. Then give each unit a tier:

| Tier | When | Who runs it |
| --- | --- | --- |
| `trivial` | One or two files, an obvious change with no design choice, and a direct check | The coordinator, per [Trivial units](#trivial-units) |
| `standard` | A clear change with a known approach that fits no complex rule | One plain Orca worker, without poteto |
| `complex` | Any complex rule below applies | One Orca worker running poteto-mode |

A unit is `complex` when any of these applies:

- It spans more than one repository, or likely more than about 5 files.
- Its design is open: several plausible approaches, a new module or public interface, or unsettled behavior.
- It touches a migration, schema, persisted or wire format, auth, secrets, or other security-sensitive code.
- The user asks for poteto or calls the work complex.

The user's words override these rules in both directions, such as "no poteto", "use poteto", or "do it yourself".

Before the first dispatch, post one line per unit: `<unit>: <tier>, <reason>`, and name the units that run in parallel. Continue without waiting for approval; the user can redirect at any time.

### Parallel units

Start independent units at the same time, each with its own worker and worktree, each tiered on its own. Units are independent when they share no files and neither needs the other's result. The coordinator does its trivial units while workers run.

A unit that needs another unit's result starts after it. Create it as an Orca task with `--deps` on that unit, base its worktree on that unit's branch with `--base-branch`, and say so in the report.

Inside its unit, a worker may run its own helpers in parallel through its native subagent tool, per the [worker contract](references/worker-contract.md#helpers).

## Ownership

| Concern | Owner |
| --- | --- |
| Units, tiers, workers, task dependencies, messages, questions, completion, cleanup | Orca coordinator |
| Trivial units | Orca coordinator, in its own worktree |
| Design, implementation, verification, commits, PR descriptions | The unit's worker |
| Poteto's prescribed reviews and short-lived helpers | Complex workers, through their native subagent tool |
| Acceptance evidence and integration between deliverables | Orca coordinator |
| Commit, push, and PR authorization | The worker's brief, per this skill |
| Merge | The user. This skill never grants it. |

When this skill and an underlying skill disagree on a concern, the owner in this table wins.

## Model configuration

Load the installed `model-picker` skill (`ultrapowers:model-picker` in Claude Code). It owns the config file, precedence, the single question, name resolution, and the dispatch audit.

Ask the picker's question only when the run has a `complex` unit or the user names a model, effort, or budget. Otherwise treat the run as "use the defaults": apply `models.yaml` through the role map without asking, and report the selections in the final report. Trivial units run in the coordinator's own session and need no selection.

Supply the picker this caller contract:

- **Role map.** Each worker's implementation and non-review helpers use `implementation`. Independent review, `interrogate` reviewers, code-review helpers, critics, cross-judges, and fix rechecks use `review`, including helpers started by implementation workers. A reviewer returns findings; assign fixes to implementation. Workers spread reviewers across the `review` entries per the [worker contract](references/worker-contract.md#review-budget).
- **Proposal units.** Every `standard` and `complex` unit, for its implementation choice.
- **Review task.** Reviewing complex units' work. The review models are shared by every unit; each added model gives workers another entry to spread reviewers across, within the budget.
- **Budget.** `review_budget` caps reviewer helpers per unit, fix rechecks included.
- **Catalog sources.** Before resolving, read Orca's `references/coordinator-loop.md` launch-preferences section. Use Orca's launch preferences and the selected agent's CLI.
- **Audit location.** Each unit's brief `LAUNCH` field and the final report.

The picker's settings override pstack and routed skills' model choices and automatic effort adjustments. A `null` inherits the selected agent's settings, not pstack's choices. Carry each unit's implementation entry and the run's review entries into that unit's brief. If a unit's selection is unavailable, stop that unit and report what is missing.

### Launch the selected runtime

Prefer `orchestration worker-start --agent` with the resolved `--model` and `--effort` when the execution host supports those overrides. Omit inherited overrides unless an explicit effort requires the default model's resolved ID. `--effort` requires `--model`.

If Orca cannot apply the overrides but the selected agent's CLI can, read `references/low-level-topology.md` and confirm `worker-start --terminal` support with the same Orca executable. Start the selected runtime with its native flags, then attach it as a supervised worker:

1. Check the installed agent's `--help` and model catalog. Build a shell-quoted command using its verified model and effort flags. For Grok Build, check `grok --help` and `grok models`; use `--model` and `--reasoning-effort` only when supported.
2. Run `ORCA terminal create --worktree <selector> --command <quoted-agent-command> --json`. Wait for readiness with `ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json` before injecting the brief. If readiness fails or is unknown, preserve the terminal and report its handle; do not start a duplicate.
3. Run `ORCA orchestration worker-start --spec <brief> --worktree <same-selector> --terminal <handle> --json`. Omit `--agent`, `--model`, and `--effort` when attaching. Use this supervised attachment rather than `dispatch --inject`. Handle a failed attachment per Orca's recovery guide and account for the existing terminal.

`ORCA` above means the executable resolved by the installed orchestration skill. Use this path only on a host whose terminal commands can target the intended workspace. If no verified route exists, stop the unit and ask for an alternative, without changing runtimes or global settings.

Compare Orca's `launch.requested` and `launch.effective` before claiming a fresh launch honored the policy. For an attached terminal, null launch overrides are not proof of model or effort: verify the runtime and actual session settings from agent metadata or CLI output. Requested flags alone are not effective-setting evidence. Reuse a terminal only when its agent, model, and effort are verified to match; `--terminal` cannot change them. Report requested and effective choices, inheritance, and any unavailable or unverifiable status.

## One coordinator

Orca owns coordination across units. Each worker owns the engineering workflow for its unit, including any helpers it spawns itself.

- Start every `standard` and `complex` unit with `orchestration worker-start`. Never start a unit with the harness subagent tool (`Agent`, `Task`, `spawn_agent`).
- Read the [worker contract](references/worker-contract.md) before writing briefs. It defines each tier's workflow and the coordination, model, permission, and completion rules without loading poteto into the coordinator.
- Dispatch a helper through Orca only when a worker asks under the contract's [helper rules](references/worker-contract.md#helpers). The worker retains ownership of that workflow.
- Check acceptance evidence and integration between deliverables. Count a complex worker's completed design and reviews toward its unit instead of repeating those phases at the coordinator level. Dispatch additional engineering review for a worker request, a user request, or a concrete integration risk.
- If a worker reports that its unit is bigger or less clear than its tier assumed, re-tier it: stop that worker and start a `complex` one with the same worktree after the first has stopped.
- During the run, the coordinator reuses, retains, or releases each settled worker per Orca's completion accounting. [Cleanup](#cleanup) ends the run.

## Workspace isolation

Separate sessions do not isolate files. Every concurrent writer, including the coordinator on a trivial unit and any editing helper, must have its own Orca-managed Git worktree and branch, distinct from the user's checkout and every other active writer's checkout. Read-only workers may share a checkout while remaining read-only.

1. Resolve the Git repositories each unit may modify with `ORCA repo list --json` and repository discovery. A project folder or Orca group containing multiple repositories is not one Git repository. Record ownership per repository.
2. Before creating worktrees, load Orca's `references/placement-and-remote.md`. From a multi-repository project root, use `orchestration worker-start --worktree new-top-level --repo <exact-repo-selector> --name <worker-name>` with the resolved launch options. Use `new-child` only within the intended Git repository, following that guide. Folder workspaces cannot become Git worktrees; never initialize the project folder as a repository to bypass this restriction.
3. For a unit that edits several repositories, provide an isolated checkout for every writable repository through supported Orca placement commands. A worktree for one repository does not isolate its siblings. If the supported commands cannot provide the required placement, split the unit into per-repository workers or report the placement blocker before edits.
4. Include the repository-to-worktree mapping in the brief. For a new worktree, specify its creation target until its actual path and branch are known. Verify the start receipt's repository, canonical checkout path, and branch against the intended placement and other active writers. Require the worker to verify its actual Git root and branch before its first write. A missing, mismatched, or shared writable checkout blocks edits; resolve it through Orca rather than falling back to `--worktree current` or the original sibling repositories.
5. Reuse an existing editing worktree only for a sequential handoff after its previous writer has stopped. This covers a worker handing its own worktree to one editing helper and resuming writes after the helper returns, and a re-tiered unit's new worker. An attached terminal must use the same verified worktree. Keep read-only helpers in their assigned scope. Concurrent editing helpers each get their own worktree through the coordinator.

## Trivial units

The coordinator does a trivial unit itself and never edits the user's checkout:

1. Create a worktree with `ORCA worktree create --name <unit> --repo <exact-repo-selector> --base-branch <baseline branch> --json`, without `--agent`. Record it from the receipt like a worker's worktree.
2. Verify the worktree's Git root and branch, then edit only there, using absolute paths or `git -C <path>`.
3. Run the repository's checks for the change and fix what fails.
4. Ship it per [Ship](#ship).

If the change turns out to need a design choice or more files, re-tier it as `standard` or `complex` and hand the worktree to a worker.

## Ship

Every unit ends as a pull request, trivial units included:

1. Commit the change on the unit's branch, using the installed `commit-style` skill when available.
2. Push only that branch with `git push -u origin <branch>`. Never force-push.
3. Open a PR against the unit's base with `gh pr create --base <base> --head <branch>`, writing the body with the installed `pr` skill when available. Complex units follow poteto's Opening a PR playbook instead.
4. Record the PR URL and the pushed head SHA. Do not merge, enable auto-merge, or wait for CI or review bots.

A unit's base is the branch the user's checkout was on at the [baseline](#baseline), a dependency's branch per [Parallel units](#parallel-units), or the base the request names.

**Authorization.** Asking for implementation through this skill authorizes, for each unit, a commit, a push of that unit's own branch, and a PR against its base. It never authorizes merge. Narrow it when the request says so: "no PR", "don't push", or "local only" means commit only, and "don't commit" means leave the change uncommitted.

If the repository has no push remote or `gh` cannot open the PR, stop after the commit and report that step as blocked. Cleanup then keeps that unit's branch.

## Coordinator steps

1. Load orchestration. Record the Cleanup [baseline](#baseline), including the run scratch directory.
2. Split the request into units and tier each per [Routing](#routing). For each unit, set its goal, constraints, repository ownership, observable acceptance, role, and authorized permissions. Post the routing lines.
3. Settle and resolve the run's models through the model picker per [Model configuration](#model-configuration). Resolve the absolute paths to the worker contract and, for complex units, poteto.
4. Write each brief per [Worker brief](#worker-brief). Start every independent worker at once per Orca's supervised loop, applying Workspace isolation and verifying the resulting placement. Do trivial units meanwhile.
5. Before accepting a settled unit, inspect its relevant diff and verification evidence against its acceptance criteria, and check that its PR exists with the reported head SHA, unless the request narrowed the [Ship](#ship) authorization. If evidence is missing or a criterion fails, return that specific gap to the responsible worker. Use the review dispatch rules above for additional review.
6. Check whether the run is [quiescent](#quiescent). If it is, run the Cleanup steps without asking. If it is not, keep every workspace.
7. Report each unit's tier, outcome, evidence, and blockers to the user, the models used, then the cleanup result: each unit's PR URL, branch, and head SHA, each worktree and local branch removed, each one kept with its reason, each checkout's restored branch, and whether the scratch directory was deleted. For a run that is not quiescent, name what it is waiting on. Finish when the requested deliverables meet acceptance and Cleanup has run.

## Cleanup

Cleanup returns the user's machine and Orca to their baseline. The deliverables live on as pull requests and their remote branches. It is automatic: it needs no confirmation once the run is quiescent, and it waits until then.

### Baseline

Before the first dispatch, record the session's working directory and, for every repository in scope, the coordinator checkout's Git root, its branch or detached SHA, and its `git status --porcelain`. Create one run scratch directory outside every checkout with `mktemp -d` and record its path. Write every brief, worker report, and other temporary file of the run there.

As the run proceeds, record every worktree, branch, worker, and terminal it creates from the receipts: exact selector, path, branch, base, Dispatch ID, terminal handle, environment, whether setup ran, and the pushed head SHA and PR URL. Cleanup touches only these recorded resources. A reused worktree, a pre-existing branch, and anything the user created stay as they are.

### Quiescent

The run is quiescent when all of these hold:

- Every Task is settled and every unit is accepted under Coordinator step 5.
- `ORCA orchestration gate-list --run <run_id>` shows no pending gate, and no question, permission request, or blocker is waiting on the user.
- `ORCA orchestration worker-list --run <run_id> --include-remote` shows no failed, unknown, or abandoned worker. Those follow Orca's recovery guide.
- The user has not asked to keep the workspaces.

An open PR is a deliverable. Its remote branch survives cleanup, and the run is quiescent with it open. Check again after each user reply that settles a pending item.

### Steps

1. Return the session to the baseline working directory.
2. Release each recorded worker with `ORCA orchestration worker-release --dispatch <dispatch_id>`. Orca keeps a new-worktree worker open after it finishes, so release it explicitly; repeating a release Orca already made is harmless. A worker the user asked to keep or took over stays open, and so does its worktree.
3. Close each recorded terminal outside a removable worktree with `ORCA terminal close --terminal <handle> --json`. Never close a terminal the run did not create or the user took over.
4. Decide which recorded worktrees are removable. A worktree is removable when `git -C <path> status --porcelain` is empty, its HEAD is on its recorded branch, and that branch's head SHA is recorded. A dirty worktree holds work that exists nowhere else, such as a `commit: no` deliverable: keep it. For a worktree on a host the coordinator cannot inspect, use the worker's reported status.
5. For each removable worktree, stop its remaining terminals with `ORCA terminal close --worktree <exact selector> --all --json`, then remove it with `ORCA worktree rm --worktree <exact selector> --json`, using the receipt's selector and environment. Add `--run-hooks` when setup ran in it, so the repository's archive hook tears down what setup created. When Orca refuses a removal, keep that worktree and report the refusal. `--force` and `--allow-failed-archive-hook` discard work or skip teardown, so cleanup never passes them.
6. Delete the local branch of each removed worktree when its commits exist elsewhere, running `git branch -d <branch>` from a remaining checkout of that repository:
   - **Pushed:** the branch's upstream is `origin/<branch>`, and `git ls-remote origin refs/heads/<branch>` returns its recorded head SHA. Git accepts `-d` because the branch matches its upstream.
   - **Empty:** `git rev-list --count <base>..<branch>` is 0.
   - Otherwise keep the branch. A commit-only unit or a blocked push makes the local branch the deliverable.

   If Git refuses, keep the branch and report it. Never use `git branch -D`.
7. Verify the result. `ORCA worktree list --json` no longer lists the removed worktrees, every PR branch on `origin` still resolves to its recorded head SHA, and every kept local branch resolves to its recorded head SHA. If a host deleted a kept branch, restore it with `git branch <branch> <sha>`.
8. Restore each coordinator checkout whose branch differs from the baseline with `git switch <branch>`, or `git switch --detach <sha>`. Switch only when its `git status --porcelain` matches the baseline. Otherwise leave it and report the difference; the user decides what happens to uncommitted work.
9. Read what the final report needs from the run scratch directory, then delete it with `rm -rf <recorded path>`. Keep it instead, and name its path in the report, when a unit is blocked or a worktree was kept.

The Run's coordination state stays in place. `orchestration reset` belongs to the user.

## Worker brief

Every `worker-start --spec` meets Orca's task-spec contract (Target, Change, Constraints, Ownership, Observable acceptance) and adds these fields:

```
TIER         standard | complex
CONTRACT     Read <absolute path to references/worker-contract.md> before any work.
SKILLS       complex only: Read <absolute path to installed poteto-mode/SKILL.md> in full.
WORKFLOW     standard: follow the contract's Standard workers section.
             complex: select the per-unit poteto playbook or review skill for your
             role. Own its execution, verification, and prescribed reviews within scope.
MODEL_POLICY Include a self-contained copy of the resolved Model configuration:
             precedence, this unit's implementation entry, every review entry,
             role routing, and the unavailable-selection rule.
REVIEW_BUDGET complex only: <n> reviewer helpers per unit, fix rechecks included | default
ROLE         implementation | review
WORKSPACES   For each repository: exact selector, writable or read-only scope,
             assigned worktree path and branch, or new-worktree creation target.
             Include the coordinator's and other active writers' checkout paths.
             Verify the actual Git root and branch before the first write.
LAUNCH       Selected runtime, configured model name, resolved provider ID, effort,
             inherited fields, resolution evidence, and supported launch route.
PERMISSIONS  The Ship authorization, narrowed by the request:
  commit:    yes | no
  push:      yes, to <branch> only | no
  pr:        yes, against base <base> | no
  merge:     no
REPORT       worker_done summary, plus --report-path <run scratch directory>/<unit>.md
             with the worker's full reply:
             actual repository roots, branches, pushed head SHAs, PR URL, commands run,
             `git status --porcelain` per checkout,
             verdict, deviations,
             requested and effective agent/model/effort, inheritance, or unavailable status,
             reviewer helpers used against REVIEW_BUDGET with each one's model
```

Grant permissions under the [worker contract](references/worker-contract.md#permissions). Carry only the [Ship](#ship) authorization, narrowed by the request, into the brief. Resolve an unavailable skill or contract path before dispatch.
