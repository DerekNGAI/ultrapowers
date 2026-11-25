---
name: model-picker
description: Suggest and select the agent, model, and effort for implementation and review before dispatching agents or workers. Use when another skill needs models picked for a run, or when asked to pick or compare models for a task.
---

# Model picker

There is no default model file. Every run, this skill suggests models for each role and the user picks them before any dispatch.

The caller supplies:

- **Units** that get an `implementation` pick, with each unit's goal and acceptance.
- **Review task**, when the run has reviewers: what they will check, and the default review budget.
- **Catalog sources**: the agents the host can launch and where to read each one's models and efforts.

## 1. Find candidates

List every launchable agent, model, and supported effort from the caller's catalog sources. Leave out anything you cannot verify as launchable.

## 2. Suggest

Rank candidates per [model proposal](references/model-proposal.md), using this ranking source: https://artificialanalysis.ai/leaderboards/models.

1. **Implementation, per unit.** Up to three rows: Best value (recommended), Lowest cost, Highest capability.
2. **Review models**, when the run has reviewers. The same three suggestions for the review task, as a multi-select. Recommend two adequate models from different providers, avoiding the implementation model when another adequate model exists. Show how many reviewer launches each added model costs.
3. **Review budget**, when the run has reviewers. The caller's default.

Skip any item the user's request already settles.

## 3. Ask and wait

The model question is required input:

1. Show the choice tables.
2. End with one plain-text question: "Reply with your pick per unit and the review models, or `recommended`."
3. End your turn. Dispatch only after the user replies.

Host rules that prefer making assumptions over asking do not cover this question. Use the host's question tool only when it allows required input; otherwise use plain text as above. Skip the question only when the request names every choice. `recommended`, or "use your recommendations", applies the recommended rows; when an item has no recommendation, ask for that pick.

## 4. Resolve names

For each pick, check the agent's model catalog on the execution host:

- A full provider ID must match exactly. A short name must equal a model's name, as a bare ID or after the provider prefix. No prefix, substring, or "latest" matches.
- No match, or several: ask the user for a full ID.
- Confirm the agent supports the chosen effort.

Never substitute a different agent, model, or effort. If a pick cannot be verified, report it unavailable.

## 5. Dispatch and record

Pass model and effort as real launch options on every dispatch. Naming them in a prompt does not select them.

| Host | Options |
| --- | --- |
| Orca | `orchestration worker-start --agent --model --effort` |
| Codex `spawn_agent` | `model`, `reasoning_effort` |
| Claude Code `Agent` | `model`, `effort` |

For each dispatch, record the role, the requested agent, model, and effort, and the effective settings from the launch receipt, or "unverified" when the host shows none. A worker's statement about its own model is not evidence.
