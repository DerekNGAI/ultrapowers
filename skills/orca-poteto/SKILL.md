---
name: orca-poteto
description: Run implementation work through Orca workers. Size the task and pick models, dispatch a plain worker for simple units and a poteto-mode worker for complex ones, ship each unit as a pull request, then clean up. Use whenever asked to implement, build, fix, refactor, or change code, and for /orca-poteto.
---

# Orca + poteto

You are the **coordinator**. You never edit code yourself; Orca workers do. Every run follows the same five steps, in order:

1. **Setup**: load Orca, record the baseline.
2. **Size and pick models**: tier each unit, ask the model question, wait.
3. **Dispatch**: one Orca worker per unit, with poteto-mode only for complex units.
4. **Finish**: accept each unit's PR.
5. **Clean up**: return the machine to the baseline.

## 1. Setup

- Load the installed `orchestration` skill, resolve its Orca executable (`ORCA` below), and run `ORCA skills get orchestration`. Use that guide for exact command syntax.
- For each repository in scope, record the checkout path, branch, and `git status --porcelain`.
- Create one scratch directory outside every checkout with `mktemp -d`. Briefs and reports go there.

## 2. Size and pick models

**Units.** Use one unit unless the request already lists separate deliverables. Do not split work further on your own.

**Tier each unit:**

| Tier | When | Worker |
| --- | --- | --- |
| `simple` | One or two files, an obvious change, a direct check | Plain Orca worker, no poteto, no reviewers |
| `complex` | Anything else | Orca worker running poteto-mode, which runs its own reviews |

The user's words override the tier: "use poteto" makes it complex, "no poteto" makes it simple.

**Order.** Run units one at a time, in the order given. Run units in parallel only when the user or the plan they gave explicitly asks for parallel work. A unit that needs another unit's result starts after it, on that unit's branch.

**Model question.** Load the installed `model-picker` skill (`ultrapowers:model-picker` in Claude Code) and give it:

- **Units**: every unit, for its `implementation` pick (the worker and its non-review helpers).
- **Review task**, only when a unit is complex: the review models fill poteto's reviewer and panel roles for complex units.
- **Poteto roles**: every complex unit, so the picker builds its role lines for the brief.
- **Catalog sources**: `ORCA agent installed --json`, and each agent's model list: `codex debug models`, `grok models`. Each model runs on its own vendor's agent: GPT on `codex`, Claude on `claude`, Grok on `grok`.

Post one message: one line per unit, `<unit>: simple|complex, <reason>`, then the picker's question. **End your turn and wait for the reply.**

## 3. Dispatch

For each unit:

1. Fill in [the worker brief](references/worker-brief.md) for its tier and save it in the scratch directory.
2. Start it with `ORCA orchestration worker-start --spec-file <brief> --agent <agent> --model <model> --effort <effort>` and a new worktree for the unit, where `<agent>` is the implementation model's own agent.
3. Check the launch receipt: the effective agent, model, and effort must match the picks.
4. While it runs, answer its `ask` messages. Forward to the user only what needs the user, including a helper worker stuck at a prompt.

**Re-tier.** If a simple worker reports that the unit needs a design choice or more files, stop it and start a complex worker on the same worktree.

**Blocked start.** When Orca reports that a worker is stuck at a prompt (hooks review, approval, trust), show the user the prompt and ask them to answer it in that terminal. Never disable hooks, change sandbox or approval flags, or hand-build a different launch to get past it. If Orca cannot apply the picked model or effort, stop and tell the user.

## 4. Finish

Each worker ships its unit as a pull request: commit, push its own branch, open a PR against the base. The base is the branch the user's checkout was on, a dependency's branch, or the base the request names. Nobody merges or enables auto-merge. "No PR" or "local only" means commit only; "don't commit" means leave the change uncommitted.

**Accept.** For each unit, read the diff and the test evidence against its acceptance, and check the PR exists at the reported head SHA. Send any gap back to the worker.

## 5. Clean up

Run this without asking once every unit is accepted and nothing waits on the user. Touch only what this run created.

1. Release each worker, and any helper worker a report lists as still open: `ORCA orchestration worker-release --dispatch <id>`.
2. For each worktree this run created: if `git status --porcelain` is empty, remove it with `ORCA worktree rm --worktree <selector> --json`. Keep a dirty one. Never pass `--force`.
3. Delete each removed worktree's local branch with `git branch -d <branch>` when it is pushed. Keep it otherwise. Never use `-D`.
4. Switch each checkout back to its baseline branch if its status still matches the baseline.
5. Delete the scratch directory, unless something was kept.

## Report

For each unit: tier, outcome, PR URL, branch, head SHA, checks run, helpers used, and the models used (requested and effective). Then the cleanup result: what was removed, what was kept and why.
