---
name: ultrapowers-model-picker
description: Suggest and select the agent, model, and effort for implementation and review before dispatching agents or workers. Use when another skill needs models picked for a run, or when asked to pick or compare models for a task.
---

# Model picker

There is no default model file. Every run, this skill suggests models for each role and the user picks them before any dispatch.

The caller supplies:

- **Units** that get an `implementation` pick, with each unit's goal and acceptance.
- **Review task**, when the run has reviewers: what they will check.
- **Poteto roles**, optional: which units need [poteto role lines](#6-poteto-role-lines).
- **Catalog sources**: the agents the host can launch and where to read each one's models and efforts.

## 1. Find candidates

List every launchable model and supported effort from the caller's catalog sources. Leave out anything you cannot verify as launchable.

Each model runs on its own vendor's agent, even when another agent's catalog also lists it:

| Vendor | Agent |
| --- | --- |
| OpenAI (GPT) | `codex` |
| Anthropic (Claude) | `claude` |
| xAI (Grok) | `grok` |

A model whose vendor's agent is not installed is not a candidate. For any other vendor, ask the user which agent runs it. When an agent has no model-list command, such as Claude Code, take its vendor's model IDs from the other catalogs and let the launch receipt confirm them.

## 2. Suggest

Rank candidates per [model proposal](references/model-proposal.md), using this ranking source: https://artificialanalysis.ai/leaderboards/models.

1. **Implementation, per unit.** Up to three rows: Best value (recommended), Lowest cost, Highest capability.
2. **Review models**, when the run has reviewers. The same three suggestions for the review task, as a multi-select. Recommend two adequate models from different providers, avoiding the implementation model when another adequate model exists. Each selected model adds one reviewer launch, so the count limits review cost.
3. **Budget**: `large` (xhigh), `medium` (high), or `small` (medium), the effort every role runs at. Recommend the lowest budget the task fit justifies, per the proposal's effort rules, and show each row at that effort.

Skip any item the user's request already settles.

## 3. Ask and wait

The model question is required input:

1. Show the choice tables.
2. End with one plain-text question: "Reply with your pick per unit, the review models, and the budget, or `recommended`."
3. End your turn. Dispatch only after the user replies.

Host rules that prefer making assumptions over asking do not cover this question. Use the host's question tool only when it allows required input; otherwise use plain text as above. Skip the question only when the request names every choice. `recommended`, or "use your recommendations", applies the recommended rows; when an item has no recommendation, ask for that pick.

## 4. Resolve names

For each pick, check the agent's model catalog on the execution host:

- A full provider ID must match exactly. A short name must equal a model's name, as a bare ID or after the provider prefix. No prefix, substring, or "latest" matches.
- No match, or several: ask the user for a full ID.
- Use the budget's effort. If the model does not support it, use its highest supported effort below it, or ask when there is none.

Never substitute a different agent, model, or effort. If a pick cannot be verified, report it unavailable.

## 5. Dispatch and record

Pass model and effort as real launch options on every dispatch. Naming them in a prompt does not select them.

| Host | Options |
| --- | --- |
| Orca | `orchestration worker-start --agent --model --effort` |
| Codex `spawn_agent` | `model`, `reasoning_effort` |
| Claude Code `Agent` | `model`, `effort` |

For each dispatch, record the role, the requested agent, model, and effort, and the effective settings from the launch receipt, or "unverified" when the host shows none. A worker's statement about its own model is not evidence.

## 6. Poteto role lines

For each unit the caller marks for poteto, build its role lines in the format of poteto's `setup-pstack` skill, so poteto runs its own flow on the picked models without a machine-wide rule file. `<effort>` is the budget's effort; `<lower>` is one step lower (xhigh, high, medium, low).

```
# pstack model configuration for this run. Overrides poteto's role defaults and any pstack-models.mdc.
# Each entry is <agent>:<model> @ <effort>.
# budget: <budget> (<effort>)
feature, refactoring: <agent>:<implementation> @ <effort>
bug-fix: <agent>:<implementation> @ <effort>
perf-issue: <agent>:<implementation> @ <effort>
hillclimb: <agent>:<implementation> @ <effort>
judgment and prose: <agent>:<implementation> @ <effort>
swarm workers: <agent>:<implementation> @ <lower>
arena runners: <agent>:<review 1> @ <effort>, <agent>:<review 2> @ <effort>, ...
arena cross-judge pool: <agent>:<review 1> @ <effort>, <agent>:<review 2> @ <effort>, ...
interrogate reviewers: <agent>:<review 1> @ <effort>, <agent>:<review 2> @ <effort>, ...
```

Use resolved model IDs. The caller decides how an entry on another agent than the worker's is launched. Never write `~/.cursor/rules/pstack-models.mdc`; the lines travel in the caller's brief.
