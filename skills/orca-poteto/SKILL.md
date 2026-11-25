---
name: orca-poteto
description: Run implementation work through Orca with poteto. Size the task and pick models, do simple work yourself or dispatch a poteto-mode Orca worker, ship a pull request, then clean up. Use whenever asked to implement, build, fix, refactor, or change code, and for /orca-poteto.
---

# Orca + poteto

You are the **coordinator**. Every run follows the same five steps, in order:

1. **Setup**: load Orca, record the baseline.
2. **Size and pick models**: tier each unit, ask the model question, wait.
3. **Do or dispatch**: do simple units yourself, give complex units to a poteto-mode worker.
4. **Finish**: ship each unit as a PR and accept it.
5. **Clean up**: return the machine to the baseline.

## 1. Setup

- Load the installed `orchestration` skill, resolve its Orca executable (`ORCA` below), and run `ORCA skills get orchestration`. Use that guide for exact command syntax.
- For each repository in scope, record the checkout path, branch, and `git status --porcelain`.
- Create one scratch directory outside every checkout with `mktemp -d`. Briefs and reports go there.

## 2. Size and pick models

**Units.** Use one unit unless the request already lists separate deliverables. Do not split work further on your own.

**Tier each unit:**

| Tier | When | Who |
| --- | --- | --- |
| `simple` | One or two files, an obvious change, a direct check | You |
| `complex` | Anything else | One Orca worker running poteto-mode |

The user's words override the tier: "use poteto" makes it complex, "do it yourself" makes it simple.

**Order.** Run units one at a time, in the order given. Run units in parallel only when the user or the plan they gave explicitly asks for parallel work. A unit that needs another unit's result starts after it, on that unit's branch.

**Model question.** When any unit is `complex`, load the installed `model-picker` skill (`ultrapowers:model-picker` in Claude Code) with these roles:

- `implementation`: one pick per complex unit, for the worker and its non-review helpers.
- `review`: the reviewer helpers' models, shared by every unit.
- `review_budget`: the maximum number of reviewer helpers per unit, fix rechecks included.

Post one message: one line per unit, `<unit>: simple|complex, <reason>`, then the picker's question. **End your turn and wait for the reply.** Skip the question only when the request names every model or says "use the defaults". A run with only simple units asks nothing.

## 3. Do or dispatch

**Simple unit.** Do it yourself, never in the user's checkout:

1. `ORCA worktree create --name <unit> --repo <repo> --base-branch <base> --json`.
2. Edit only in that worktree. Run the repository's checks for the change and fix failures.
3. If it turns out to need a design choice or more files, make it complex and dispatch a worker to the same worktree.

**Complex unit.** Dispatch one worker:

1. Fill in [the worker brief](references/worker-brief.md) and save it in the scratch directory.
2. Start it with `ORCA orchestration worker-start --spec-file <brief> --agent <agent> --model <model> --effort <effort>` and a new worktree for the unit. Omit `--model` or `--effort` only for a `null` (inherit) pick.
3. Check the launch receipt: the requested and effective agent, model, and effort must match the picks.
4. While it runs, answer its `ask` messages. Forward to the user only what needs the user.

**Blocked start.** When Orca reports that a worker is stuck at a prompt (hooks review, approval, trust), show the user the prompt and ask them to answer it in that terminal. Never disable hooks, change sandbox or approval flags, or hand-build a different launch to get past it. If Orca cannot apply the picked model or effort, stop and tell the user.

## 4. Finish

**Ship.** Every unit ends as a pull request:

1. Commit on the unit's branch, using the installed `commit-style` skill when available.
2. `git push -u origin <branch>`. Never force-push.
3. `gh pr create --base <base> --head <branch>`, with the body written by the installed `pr` skill when available.

The base is the branch the user's checkout was on, a dependency's branch, or the base the request names. Workers ship their own unit; you ship simple units. Never merge or enable auto-merge. "No PR" or "local only" means commit only; "don't commit" means leave the change uncommitted. If push or PR creation fails, keep the commit and report the step as blocked.

**Accept.** For each unit, read the diff and the test evidence against its acceptance, and check the PR exists at the reported head SHA. Send any gap back to the worker.

## 5. Clean up

Run this without asking once every unit is accepted and nothing waits on the user. Touch only what this run created.

1. Release each worker: `ORCA orchestration worker-release --dispatch <id>`.
2. For each worktree this run created: if `git status --porcelain` is empty, remove it with `ORCA worktree rm --worktree <selector> --json`. Keep a dirty one. Never pass `--force`.
3. Delete each removed worktree's local branch with `git branch -d <branch>` when it is pushed. Keep it otherwise. Never use `-D`.
4. Switch each checkout back to its baseline branch if its status still matches the baseline.
5. Delete the scratch directory, unless something was kept.

## Report

For each unit: tier, outcome, PR URL, branch, head SHA, checks run, and the models used (requested and effective). Then the cleanup result: what was removed, what was kept and why.
