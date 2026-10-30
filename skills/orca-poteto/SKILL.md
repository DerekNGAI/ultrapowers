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

## Model configuration

Read [models.yaml](models.yaml) beside the loaded `SKILL.md` at the start of every run, not relative to the project's working directory. It is the only source of this skill's agent, model, and effort defaults. Require both `implementation` and `review`, each with exactly these fields:

- `agent`: a nonempty Orca agent ID. It selects the runtime, not the model provider.
- `model`: a nonempty short model name, a full provider ID, or YAML `null` to inherit the selected agent's configured default.
- `effort`: a nonempty effort name, or YAML `null` to inherit that agent/model's configured default.

If the file is missing or invalid, stop before dispatch and report the path and error. Missing fields, duplicate keys, empty strings, and unknown fields are invalid, not requests to inherit defaults.

Apply the user's explicit overrides for this run field by field over the file. Leave the file unchanged unless the user asks to save the choices. These settings override pstack and routed skills' model choices and automatic effort adjustments. A `null` inherits the selected agent's settings, not pstack's choices. Leave global agent settings and project files unchanged.

Use `implementation` for implementation and non-review helpers. Use `review` for independent review, `interrogate` reviewers, code-review helpers, critics, and cross-judges, including helpers started by implementation workers. Preserve the routed skill's reviewer count unless the user overrides it. A reviewer returns findings; assign fixes to implementation.

### Resolve model names

Before dispatch, read Orca's `references/coordinator-loop.md` launch-preferences section. Resolve each role against the execution host's selected agent, available model catalog, configured default, and supported efforts:

1. Verify the configured agent exists on that host. Keep that runtime fixed throughout resolution. A runtime running the same model is not a substitute for the configured agent.
2. For a full provider ID, require an exact available match. For a short name, collect models whose complete model name matches exactly, either as a bare ID or after the provider prefix. Use the catalog's model-name field when available; otherwise compare the final slash-delimited segment. Do not use substring, prefix, latest-version, or context-variant matches.
3. When a short name has multiple matches, prefer the selected agent's configured provider only if its settings or default model identify that provider unambiguously. Do not privilege a bare ID over a provider-qualified ID. If exactly one match remains, use its exact launch ID. Otherwise report the candidates or missing name and ask for a full ID before dispatch.
4. Verify the requested effort for the resolved model through the host's catalog or CLI. If `model` is `null` but effort is explicit, resolve the agent's configured default model first so a launch requiring `--model` can apply `--effort`. Keep inherited fields marked as inherited in the report.
5. Record the configured name, resolved ID, agent, effort, and resolution evidence in the worker brief. If availability, provider preference, or effort support cannot be verified, stop that unit and report what is missing. Never silently change the agent, model, or effort.

Resolve choices once per run and carry them into every worker brief. A worker uses that resolved policy rather than loading a different installed copy of the config. If a later dispatch encounters a changed catalog or unavailable selection, stop and report it rather than reinterpreting the short name.

### Launch the selected runtime

Prefer `orchestration worker-start --agent` with the resolved `--model` and `--effort` when the execution host supports those overrides. Omit inherited overrides unless an explicit effort requires the default model's resolved ID. `--effort` requires `--model`.

If Orca cannot apply the overrides but the selected agent's CLI can, read `references/low-level-topology.md` and confirm `worker-start --terminal` support with the same Orca executable. Start the selected runtime with its native flags, then attach it as a supervised worker:

1. Check the installed agent's `--help` and model catalog. Build a shell-quoted command using its verified model and effort flags. For Grok Build, check `grok --help` and `grok models`; use `--model` and `--reasoning-effort` only when supported.
2. Run `ORCA terminal create --worktree <selector> --command <quoted-agent-command> --json`. Wait for readiness with `ORCA terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json` before injecting the brief. If readiness fails or is unknown, preserve the terminal and report its handle; do not start a duplicate.
3. Run `ORCA orchestration worker-start --spec <brief> --worktree <same-selector> --terminal <handle> --json`. Omit `--agent`, `--model`, and `--effort` when attaching. Use this supervised attachment rather than `dispatch --inject`. Handle a failed attachment per Orca's recovery guide and account for the existing terminal.

`ORCA` above means the executable resolved by the installed orchestration skill. Use this path only on a host whose terminal commands can target the intended workspace. If no verified route exists, stop the unit and ask for an alternative, without changing runtimes or global settings.

A short-lived harness helper is allowed only if it can honor the resolved agent, model, and effort. Otherwise the worker asks the coordinator to dispatch that helper through Orca; it does not start an Orca worker itself. A model override alone does not change a helper's runtime.

Compare Orca's `launch.requested` and `launch.effective` before claiming a fresh launch honored the policy. For an attached terminal, null launch overrides are not proof of model or effort: verify the runtime and actual session settings from agent metadata or CLI output. Requested flags alone are not effective-setting evidence. Reuse a terminal only when its agent, model, and effort are verified to match; `--terminal` cannot change them. Report requested and effective choices, inheritance, and any unavailable or unverifiable status.

## One coordinator

Orca is the only coordinator. poteto runs inside each unit of work, never above it.

- Do not run poteto's Orchestrate, Autopilot-full, or Autopilot-stack playbooks, or its `scripts/orch` store. When poteto's routing picks one of them, run Orca's supervised loop instead and apply poteto's per-unit playbook (Feature, Bug fix, Refactoring, and so on) inside each worker.
- Start every unit of work with `orchestration worker-start`. Never start a unit with the harness subagent tool (`Agent`, `Task`, `spawn_agent`).
- A worker may use poteto's short-lived helpers that finish inside its own turn, such as `interrogate`, `architect`, or `swarm` verification. A worker does not start Orca workers.
- A worker asks questions with the `ask` command from its Orca preamble, never with a local question tool. poteto's question rules still decide whether a question is worth asking.
- A worker reports completion once, with `worker_done`. It writes poteto's full reply to a file and passes that file as `--report-path`.
- The coordinator reuses, retains, or releases each settled worker per Orca's completion accounting.

## Coordinator steps

1. Load both skills and the sibling `models.yaml`. Resolve the Model configuration for this run.
2. Split the request into units. For each unit, pick its implementation or review role, the poteto playbook, and the permissions the user granted.
3. Write each brief per the next section. Start workers per Orca's supervised loop.
4. Before you accept a settled unit, read its diff and its verification evidence, per poteto's Subagents section. An independent review is its own Orca task, in a separate worker session from the author.
5. Report to the user with Orca's per-task outcome, evidence, and blockers, written per poteto's Writing the reply.

## Worker brief

Every `worker-start --spec` meets Orca's task-spec contract (Target, Change, Constraints, Ownership, Observable acceptance) and adds these fields:

```
SKILLS       Read poteto-mode's SKILL.md in full before any work. Follow its <playbook> playbook.
MODEL_POLICY Include a self-contained copy of the resolved Model configuration,
             including its precedence, both roles, helper routing, and unavailable-selection rule.
ROLE         implementation | review
LAUNCH       Selected runtime, configured model name, resolved provider ID, effort,
             inherited fields, resolution evidence, and supported launch route.
PERMISSIONS
  commit:    yes | no
  push:      no | yes, to <branch> only
  pr:        no | yes, against base <branch>
  merge:     no
REPORT       worker_done summary, plus --report-path to poteto's full reply:
             branch, head SHA, PR URL, commands run, verdict, deviations,
             requested and effective agent/model/effort, inheritance, or unavailable status
```

## Permissions

- A missing or unclear line means no.
- A grant covers only the named branch or base, and only the files in the brief's Ownership.
- The coordinator grants only what the user granted to it. It cannot grant merge.
- These lines override poteto's Autonomy section for git and forge actions. poteto's Always-pause list still applies.
- Never, under any grant: merge, enable auto-merge, force-push, retarget an existing PR, or rebase a branch that another agent uses.
- With `commit: yes`, poteto's commit rules apply. With `pr: yes`, poteto's Opening a PR playbook applies. The worker posts the PR URL and does not babysit or ship.
- If the work needs a permission the brief does not grant, stop at the last allowed step and `ask` the coordinator. The coordinator asks the user.
