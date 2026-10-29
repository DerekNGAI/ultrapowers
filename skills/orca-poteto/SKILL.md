---
name: orca-poteto
description: Run multi-agent engineering work with Orca as the only coordinator and poteto-mode as the engineering standard for every worker. Use for /orca-poteto, or when asked to coordinate Orca workers that work in poteto's style.
disable-model-invocation: true
---

# Orca + poteto

This skill is a thin wrapper. It sets the boundary between two installed skills and adds a permission contract for workers. It does not copy either skill. Load both from their installed copies at the start of every run, so their updates apply:

- **orchestration** (Orca). Resolve the executable per the installed `orchestration` skill, then run `ORCA skills get orchestration`. The binary serves the version-matched guide.
- **poteto-mode** (poteto). Read its installed `SKILL.md` in full, then the playbooks and principle skills it routes to.

Status: a recommended adaptation, not a tested integration. If a rule here contradicts the current behavior of either skill, stop and report the conflict to the user. Do not improvise a merge of the two.

## Ownership

| Concern | Owner |
| --- | --- |
| Workers, task dependencies, messages, questions, completion, cleanup | Orca |
| Design, implementation, verification, commits, PR descriptions | poteto |
| Commit, push, and PR authorization | The worker's brief, per this skill |
| Merge | The user. This skill never grants it. |

When the two skills disagree on a concern, the owner in this table wins.

## One coordinator

Orca is the only coordinator. poteto runs inside each unit of work, never above it.

- Do not run poteto's Orchestrate, Autopilot-full, or Autopilot-stack playbooks, or its `scripts/orch` store. When poteto's routing picks one of them, run Orca's supervised loop instead and apply poteto's per-unit playbook (Feature, Bug fix, Refactoring, and so on) inside each worker.
- Start every unit of work with `orchestration worker-start`. Never start a unit with the harness subagent tool (`Agent`, `Task`, `spawn_agent`).
- A worker may use poteto's short-lived helpers that finish inside its own turn, such as `interrogate`, `architect`, or `swarm` verification. A worker does not start Orca workers.
- A worker asks questions with the `ask` command from its Orca preamble, never with a local question tool. poteto's question rules still decide whether a question is worth asking.
- A worker reports completion once, with `worker_done`. It writes poteto's full reply to a file and passes that file as `--report-path`.
- The coordinator reuses, retains, or releases each settled worker per Orca's completion accounting.

## Coordinator steps

1. Load both skills.
2. Split the request into units. For each unit, pick the poteto playbook and the permissions the user granted.
3. Write each brief per the next section. Start workers per Orca's supervised loop.
4. Before you accept a settled unit, read its diff and its verification evidence, per poteto's Subagents section. An independent review is its own Orca task, on a different agent from the author.
5. Report to the user with Orca's per-task outcome, evidence, and blockers, written per poteto's Writing the reply.

## Worker brief

Every `worker-start --spec` meets Orca's task-spec contract (Target, Change, Constraints, Ownership, Observable acceptance) and adds these fields:

```
SKILLS       Read poteto-mode's SKILL.md in full before any work. Follow its <playbook> playbook.
PERMISSIONS
  commit:    yes | no
  push:      no | yes, to <branch> only
  pr:        no | yes, against base <branch>
  merge:     no
REPORT       worker_done summary, plus --report-path to poteto's full reply:
             branch, head SHA, PR URL, commands run, verdict, deviations
```

## Permissions

- A missing or unclear line means no.
- A grant covers only the named branch or base, and only the files in the brief's Ownership.
- The coordinator grants only what the user granted to it. It cannot grant merge.
- These lines override poteto's Autonomy section for git and forge actions. poteto's Always-pause list still applies.
- Never, under any grant: merge, enable auto-merge, force-push, retarget an existing PR, or rebase a branch that another agent uses.
- With `commit: yes`, poteto's commit rules apply. With `pr: yes`, poteto's Opening a PR playbook applies. The worker posts the PR URL and does not babysit or ship.
- If the work needs a permission the brief does not grant, stop at the last allowed step and `ask` the coordinator. The coordinator asks the user.
