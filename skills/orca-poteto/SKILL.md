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

## Model selection

This skill's policy applies in every project where it is installed and invoked. Resolve choices in this order: the user's explicit request for this run, this policy, pstack model settings, then the routed skill's defaults. This is an intentional override of poteto's model selection, not a conflict requiring a stop. Leave global pstack settings and project files unchanged.

| Work | Model | Reasoning effort |
| --- | --- | --- |
| Implementation and non-review helpers | The selected agent's configured default | Configured default |
| Independent review and review helpers | Grok 4.6 | xhigh |

Review includes `interrogate` reviewers, code-review helpers, critics, and cross-judges, even when an implementation worker starts them. A reviewer returns findings; assign subsequent fixes to implementation so the review model does not become the implementation default.

Before dispatch, read Orca's `references/coordinator-loop.md` launch-preferences section and resolve the policy against the execution host's available agents, model IDs, and supported efforts:

- **Implementation:** keep the selected/configured agent and omit `--model` and `--effort` on fresh Orca launches. Non-review harness helpers omit their model and effort overrides to inherit their parent's defaults. These choices override poteto's explicit code and hardest-task models.
- **Review:** use an agent that actually exposes Grok 4.6 with xhigh reasoning. Resolve its exact provider ID from the host's model catalog or CLI; the display name here is not a verified launch slug. Set the model and effort through that agent's supported launch mechanism. Keep xhigh fixed rather than applying poteto's automatic effort adjustments. A helper uses the corresponding harness options. Every `interrogate reviewers` entry uses this selection; preserve the routed skill's reviewer count unless the user overrides it.
- **Unavailable selection:** if the exact review model or effort cannot be verified or selected, stop that review and report what is missing. Never silently substitute Opus, another Grok version, lower effort, or the parent model. A worker whose helper tool cannot launch it asks the coordinator to dispatch the review through Orca; it does not start an Orca worker itself. If no supported route exists, ask the user for an alternative.
- **Launch evidence:** compare Orca's `launch.requested` and `launch.effective` before claiming the policy was honored. Reuse a terminal for a different role only when its existing model and effort are verified to match; `--terminal` cannot change them. Record requested and effective choices, or unavailable status, in the report.

## One coordinator

Orca is the only coordinator. poteto runs inside each unit of work, never above it.

- Do not run poteto's Orchestrate, Autopilot-full, or Autopilot-stack playbooks, or its `scripts/orch` store. When poteto's routing picks one of them, run Orca's supervised loop instead and apply poteto's per-unit playbook (Feature, Bug fix, Refactoring, and so on) inside each worker.
- Start every unit of work with `orchestration worker-start`. Never start a unit with the harness subagent tool (`Agent`, `Task`, `spawn_agent`).
- A worker may use poteto's short-lived helpers that finish inside its own turn, such as `interrogate`, `architect`, or `swarm` verification. A worker does not start Orca workers.
- A worker asks questions with the `ask` command from its Orca preamble, never with a local question tool. poteto's question rules still decide whether a question is worth asking.
- A worker reports completion once, with `worker_done`. It writes poteto's full reply to a file and passes that file as `--report-path`.
- The coordinator reuses, retains, or releases each settled worker per Orca's completion accounting.

## Coordinator steps

1. Load both skills and resolve the Model selection policy for this run.
2. Split the request into units. For each unit, pick its implementation or review role, the poteto playbook, and the permissions the user granted.
3. Write each brief per the next section. Start workers per Orca's supervised loop.
4. Before you accept a settled unit, read its diff and its verification evidence, per poteto's Subagents section. An independent review is its own Orca task, on a different agent from the author.
5. Report to the user with Orca's per-task outcome, evidence, and blockers, written per poteto's Writing the reply.

## Worker brief

Every `worker-start --spec` meets Orca's task-spec contract (Target, Change, Constraints, Ownership, Observable acceptance) and adds these fields:

```
SKILLS       Read poteto-mode's SKILL.md in full before any work. Follow its <playbook> playbook.
MODEL_POLICY Include a self-contained copy of the resolved Model selection policy,
             including its precedence, both roles, helper routing, and unavailable-selection rule.
ROLE         implementation | review
LAUNCH       Selected agent and resolved model/effort, or configured defaults.
PERMISSIONS
  commit:    yes | no
  push:      no | yes, to <branch> only
  pr:        no | yes, against base <branch>
  merge:     no
REPORT       worker_done summary, plus --report-path to poteto's full reply:
             branch, head SHA, PR URL, commands run, verdict, deviations,
             requested and effective model/effort or unavailable status
```

## Permissions

- A missing or unclear line means no.
- A grant covers only the named branch or base, and only the files in the brief's Ownership.
- The coordinator grants only what the user granted to it. It cannot grant merge.
- These lines override poteto's Autonomy section for git and forge actions. poteto's Always-pause list still applies.
- Never, under any grant: merge, enable auto-merge, force-push, retarget an existing PR, or rebase a branch that another agent uses.
- With `commit: yes`, poteto's commit rules apply. With `pr: yes`, poteto's Opening a PR playbook applies. The worker posts the PR URL and does not babysit or ship.
- If the work needs a permission the brief does not grant, stop at the last allowed step and `ask` the coordinator. The coordinator asks the user.
