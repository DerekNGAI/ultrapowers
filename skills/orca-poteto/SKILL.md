---
name: orca-poteto
description: Coordinate Orca workers that run poteto-mode in separate sessions. The coordinator uses orchestration, and each worker owns its engineering workflow. Use for /orca-poteto, or when asked to coordinate Orca workers that work in poteto's style.
disable-model-invocation: true
---

# Orca + poteto

This wrapper separates Orca coordination from poteto engineering. Its rules apply only to this run and its workers. Leave the installed `orchestration` and `poteto-mode` skills and their standalone settings unchanged.

- **Coordinator.** Load the installed `orchestration` skill, resolve its executable, then run `ORCA skills get orchestration`. Follow that version-matched guide and this wrapper. Locate the installed `poteto-mode/SKILL.md` without loading its contents or routed skills into the coordinator session.
- **Workers.** Start separate sessions with bounded task briefs and the needed file pointers. Each worker loads the installed poteto skill, selects its own per-unit playbook, and spawns its own short-lived helpers. Pass the absolute skill path and the [worker contract](references/worker-contract.md) in the brief instead of the coordinator's full transcript or this coordinator guide.

Status: a recommended adaptation with limited run testing. If a rule here contradicts the current behavior of either skill, stop and report the conflict to the user. Do not improvise a merge of the two.

## Ownership

| Concern | Owner |
| --- | --- |
| Workers, task dependencies, messages, questions, completion, cleanup | Orca coordinator |
| Design, implementation, verification, prescribed reviews, commits, PR descriptions | poteto workers |
| Short-lived helpers: reviewers, sketchers, explainers, verifiers | poteto workers, through their native subagent tool |
| Acceptance evidence and integration between workers' deliverables | Orca coordinator |
| Commit, push, and PR authorization | The worker's brief, per this skill |
| Merge | The user. This skill never grants it. |

When the two skills disagree on a concern, the owner in this table wins.

## Model configuration

Read [models.yaml](models.yaml) beside the loaded `SKILL.md` at the start of every run, not relative to the project's working directory. It is the only source of this skill's defaults. Require exactly these keys:

- `implementation`: one entry. It is the default for every unit.
- `review`: a nonempty list of entries. Several entries spread reviewers across models.
- `review_budget`: a positive integer capping reviewer helpers per unit, or YAML `null` to keep each routed skill's reviewer count.
- `ranking_source`: a nonempty URL of a public model leaderboard, or YAML `null` to run every unit on `implementation`.

Each entry has exactly these fields:

- `agent`: a nonempty Orca agent ID. It selects the runtime, not the model provider.
- `model`: a nonempty short model name, a full provider ID, or YAML `null` to inherit the selected agent's configured default.
- `effort`: a nonempty effort name, or YAML `null` to inherit that agent/model's configured default.

If the file is missing or invalid, stop before dispatch and report the path and error. Missing fields, duplicate keys, empty strings, empty lists, and unknown fields are invalid, not requests to inherit defaults.

### Propose and ask

After splitting the request into units, ask the user once, in a single message, for this run's:

1. Implementation agent, model, and effort for each unit.
2. Reviewer entries: one or more agent, model, and effort choices, shared by every unit.
3. Review budget: the most reviewer helpers one unit may start, or poteto's default counts.

For item 1, build a per-unit proposal by following [model proposal](references/model-proposal.md) and show its table. For items 2 and 3, offer the file's value as the default. The user approves or edits the message before any dispatch.

Skip an item the user's request already settles. An implementation model named in the request applies to every unit it covers and replaces their proposal. Skip the message when the request settles all three or says to use the defaults; then every unit runs on the file's `implementation` entry. Use the host's question tool when it has one; otherwise ask in chat and wait for the reply.

Apply the approved answers and any other explicit overrides field by field over the file. Leave the file unchanged unless the user asks to save the choices. These settings override pstack and routed skills' model choices and automatic effort adjustments. A `null` inherits the selected agent's settings, not pstack's choices. Leave global agent settings and project files unchanged.

Use the unit's implementation entry for its implementation and non-review helpers. Use `review` for independent review, `interrogate` reviewers, code-review helpers, critics, cross-judges, and fix rechecks, including helpers started by implementation workers. A reviewer returns findings; assign fixes to implementation. Workers apply `review_budget` and spread reviewers across the `review` entries per the [worker contract](references/worker-contract.md#review-budget).

### Resolve model names

Before dispatch, read Orca's `references/coordinator-loop.md` launch-preferences section. Resolve each unit's implementation entry and every review entry against the execution host's selected agent, available model catalog, configured default, and supported efforts:

1. Verify the configured agent exists on that host. Keep that runtime fixed throughout resolution. A runtime running the same model is not a substitute for the configured agent.
2. For a full provider ID, require an exact available match. For a short name, collect models whose complete model name matches exactly, either as a bare ID or after the provider prefix. Use the catalog's model-name field when available; otherwise compare the final slash-delimited segment. Do not use substring, prefix, latest-version, or context-variant matches.
3. When a short name has multiple matches, prefer the selected agent's configured provider only if its settings or default model identify that provider unambiguously. Do not privilege a bare ID over a provider-qualified ID. If exactly one match remains, use its exact launch ID. Otherwise report the candidates or missing name and ask for a full ID before dispatch.
4. Verify the requested effort for the resolved model through the host's catalog or CLI. If `model` is `null` but effort is explicit, resolve the agent's configured default model first so a launch requiring `--model` can apply `--effort`. Keep inherited fields marked as inherited in the report.
5. Record the configured name, resolved ID, agent, effort, and resolution evidence in the worker brief. If availability, provider preference, or effort support cannot be verified, stop that unit and report what is missing. Never silently change the agent, model, or effort.

Resolve each distinct choice once per run. Carry each unit's implementation entry and the run's review entries into that unit's brief. A worker uses that resolved policy rather than loading a different installed copy of the config. If a later dispatch encounters a changed catalog or unavailable selection, stop and report it rather than reinterpreting the short name.

### Launch the selected runtime

Prefer `orchestration worker-start --agent` with the resolved `--model` and `--effort` when the execution host supports those overrides. Omit inherited overrides unless an explicit effort requires the default model's resolved ID. `--effort` requires `--model`.

If Orca cannot apply the overrides but the selected agent's CLI can, read `references/low-level-topology.md` and confirm `worker-start --terminal` support with the same Orca executable. Start the selected runtime with its native flags, then attach it as a supervised worker:

1. Check the installed agent's `--help` and model catalog. Build a shell-quoted command using its verified model and effort flags. For Grok Build, check `grok --help` and `grok models`; use `--model` and `--reasoning-effort` only when supported.
2. Run `ORCA terminal create --worktree <selector> --command <quoted-agent-command> --json`. Wait for readiness with `ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json` before injecting the brief. If readiness fails or is unknown, preserve the terminal and report its handle; do not start a duplicate.
3. Run `ORCA orchestration worker-start --spec <brief> --worktree <same-selector> --terminal <handle> --json`. Omit `--agent`, `--model`, and `--effort` when attaching. Use this supervised attachment rather than `dispatch --inject`. Handle a failed attachment per Orca's recovery guide and account for the existing terminal.

`ORCA` above means the executable resolved by the installed orchestration skill. Use this path only on a host whose terminal commands can target the intended workspace. If no verified route exists, stop the unit and ask for an alternative, without changing runtimes or global settings.

Compare Orca's `launch.requested` and `launch.effective` before claiming a fresh launch honored the policy. For an attached terminal, null launch overrides are not proof of model or effort: verify the runtime and actual session settings from agent metadata or CLI output. Requested flags alone are not effective-setting evidence. Reuse a terminal only when its agent, model, and effort are verified to match; `--terminal` cannot change them. Report requested and effective choices, inheritance, and any unavailable or unverifiable status.

## One coordinator

Orca owns coordination across tasks. Each poteto worker owns the engineering workflow for its assigned unit, including its prescribed reviews and short-lived helpers, which it spawns itself.

- Start every unit of work with `orchestration worker-start`. Never start a unit with the harness subagent tool (`Agent`, `Task`, `spawn_agent`).
- Read the [worker contract](references/worker-contract.md) before writing briefs. It defines the worker's coordination, model, permission, and completion rules without loading poteto into the coordinator.
- Dispatch a helper through Orca only when a worker asks under the contract's [helper rules](references/worker-contract.md#helpers). The worker retains ownership of that workflow.
- Check acceptance evidence and integration between deliverables. Count the worker's completed design and reviews toward that task instead of repeating those phases at the coordinator level. Dispatch additional engineering review for a worker request, a user request, or a concrete integration risk.
- During the run, the coordinator reuses, retains, or releases each settled worker per Orca's completion accounting. [Cleanup](#cleanup) ends the run.

## Workspace isolation

Separate sessions do not isolate files. Every concurrent writer, including an editing helper, must have its own Orca-managed Git worktree and branch, distinct from the coordinator's checkout and every other active writer's checkout. Read-only workers may share a checkout while remaining read-only.

1. Resolve the Git repositories each unit may modify with `ORCA repo list --json` and repository discovery. A project folder or Orca group containing multiple repositories is not one Git repository. Record ownership per repository.
2. Before creating worktrees, load Orca's `references/placement-and-remote.md`. From a multi-repository project root, use `orchestration worker-start --worktree new-top-level --repo <exact-repo-selector> --name <worker-name>` with the resolved launch options. Use `new-child` only within the intended Git repository, following that guide. Folder workspaces cannot become Git worktrees; never initialize the project folder as a repository to bypass this restriction.
3. For a unit that edits several repositories, provide an isolated checkout for every writable repository through supported Orca placement commands. A worktree for one repository does not isolate its siblings. If the supported commands cannot provide the required placement, split the unit into per-repository workers or report the placement blocker before edits.
4. Include the repository-to-worktree mapping in the brief. For a new worktree, specify its creation target until its actual path and branch are known. Verify the start receipt's repository, canonical checkout path, and branch against the intended placement and other active writers. Require the worker to verify its actual Git root and branch before its first write. A missing, mismatched, or shared writable checkout blocks edits; resolve it through Orca rather than falling back to `--worktree current` or the original sibling repositories.
5. Reuse an existing editing worktree only for a sequential handoff after its previous writer has stopped. This covers a worker handing its own worktree to one editing helper and resuming writes after the helper returns. An attached terminal must use the same verified worktree. Keep read-only helpers in their assigned scope. Concurrent editing helpers each get their own worktree through the coordinator.

## Coordinator steps

1. Load orchestration and the sibling `models.yaml`. Resolve the absolute paths to poteto and the worker contract. Record the Cleanup [baseline](#baseline).
2. Split the request into bounded units. For each unit, set its goal, constraints, repository ownership, observable acceptance, implementation or review role, and authorized permissions. Leave playbook selection to the worker.
3. Settle the run's models per [Propose and ask](#propose-and-ask), then resolve them per [Resolve model names](#resolve-model-names).
4. Write each brief per the next section. Start separate worker sessions per Orca's supervised loop, applying Workspace isolation and verifying the resulting placement.
5. Before accepting a settled unit, inspect its relevant diff and verification evidence against its acceptance criteria. If evidence is missing or a criterion fails, return that specific gap to the responsible worker. Use the review dispatch rules above for additional review.
6. Check whether the run is [quiescent](#quiescent). If it is, run the Cleanup steps without asking. If it is not, keep every workspace.
7. Report each task's outcome, evidence, and blockers to the user, then the cleanup result: each worktree removed, each one kept with its reason, each deliverable's branch, head SHA, and PR URL, and each checkout's restored branch. For a run that is not quiescent, name what it is waiting on. Finish when the requested deliverables meet acceptance and Cleanup has run.

## Cleanup

Cleanup returns the user's Orca to its baseline and keeps the deliverables. It is automatic: it needs no confirmation once the run is quiescent, and it waits until then.

### Baseline

Before the first dispatch, record the session's working directory and, for every repository in scope, the coordinator checkout's Git root, its branch or detached SHA, and its `git status --porcelain`.

As the run proceeds, record every worktree, branch, and worker it creates from the start receipts: exact selector, path, branch, base, Dispatch ID, environment, and whether setup ran. Cleanup touches only these recorded resources. A reused worktree, a pre-existing branch, and anything the user created stay as they are.

### Quiescent

The run is quiescent when all of these hold:

- Every Task is settled and every unit is accepted under Coordinator step 5.
- `ORCA orchestration gate-list --run <run_id>` shows no pending gate, and no question, permission request, or blocker is waiting on the user.
- `ORCA orchestration worker-list --run <run_id> --include-remote` shows no failed, unknown, or abandoned worker. Those follow Orca's recovery guide.
- The user has not asked to keep the workspaces.

An unmerged branch or an open PR is a deliverable. It survives cleanup, and the run is quiescent with it open. Check again after each user reply that settles a pending item.

### Steps

1. Return the session to the baseline working directory.
2. Release each recorded worker with `ORCA orchestration worker-release --dispatch <dispatch_id>`. Orca keeps a new-worktree worker open after it finishes, so release it explicitly. A worker the user asked to keep or took over stays open, and so does its worktree.
3. Decide which recorded worktrees are removable. A worktree is removable when `git -C <path> status --porcelain` is empty, its HEAD is on its recorded branch, and that branch's head SHA is recorded. A dirty worktree holds work that exists nowhere else, such as a `commit: no` deliverable: keep it. For a worktree on a host the coordinator cannot inspect, use the worker's reported status.
4. Remove each removable worktree with `ORCA worktree rm --worktree <exact selector> --json`, using the start receipt's selector and environment. Add `--run-hooks` when setup ran in it, so the repository's archive hook tears down what setup created. Add `--delete-branch` only when `git rev-list --count <base>..<branch>` is 0. When Orca refuses a removal, keep that worktree and report the refusal. `--force` and `--allow-failed-archive-hook` discard work or skip teardown, so cleanup never passes them.
5. Verify the result. `ORCA worktree list --json` no longer lists the removed worktrees, and every deliverable branch still resolves to its recorded head SHA. If a host deleted one, restore it with `git branch <branch> <sha>`.
6. Restore each coordinator checkout whose branch differs from the baseline with `git switch <branch>`, or `git switch --detach <sha>`. Switch only when its `git status --porcelain` matches the baseline. Otherwise leave it and report the difference; the user decides what happens to uncommitted work.

The Run's coordination state stays in place. `orchestration reset` belongs to the user.

## Worker brief

Every `worker-start --spec` meets Orca's task-spec contract (Target, Change, Constraints, Ownership, Observable acceptance) and adds these fields:

```
CONTRACT     Read <absolute path to references/worker-contract.md> before any work.
SKILLS       Read <absolute path to installed poteto-mode/SKILL.md> in full.
WORKFLOW     Select the per-unit poteto playbook or review skill for your role.
             Own its execution, verification, and prescribed reviews within scope.
MODEL_POLICY Include a self-contained copy of the resolved Model configuration:
             precedence, this unit's implementation entry, every review entry,
             role routing, and the unavailable-selection rule.
REVIEW_BUDGET <n> reviewer helpers per unit, fix rechecks included | default
ROLE         implementation | review
WORKSPACES   For each repository: exact selector, writable or read-only scope,
             assigned worktree path and branch, or new-worktree creation target.
             Include the coordinator's and other active writers' checkout paths.
             Verify the actual Git root and branch before the first write.
LAUNCH       Selected runtime, configured model name, resolved provider ID, effort,
             inherited fields, resolution evidence, and supported launch route.
PERMISSIONS
  commit:    yes | no
  push:      no | yes, to <branch> only
  pr:        no | yes, against base <branch>
  merge:     no
REPORT       worker_done summary, plus --report-path to poteto's full reply:
             actual repository roots, branches, head SHAs, PR URL, commands run,
             `git status --porcelain` per checkout,
             verdict, deviations,
             requested and effective agent/model/effort, inheritance, or unavailable status,
             reviewer helpers used against REVIEW_BUDGET with each one's model
```

Grant permissions under the [worker contract](references/worker-contract.md#permissions). Carry only the user's existing authorization into the brief. Resolve an unavailable skill or contract path before dispatch.
