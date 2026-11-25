---
name: model-picker
description: Select the agent, model, and effort for each role before dispatching agents or workers. Use when another skill needs models resolved for a run, or when asked to pick or compare models for a task.
---

# Model picker

The caller names its roles (`implementation`, `review`), the units that get an implementation pick, and what reviewers will check. This skill returns one agent, model, and effort per role, chosen by the user, before any dispatch.

## 1. Load the config

Read [models.yaml](models.yaml) beside this file, following symlinks, never from the project being worked on. It needs exactly these keys:

- `implementation`: one entry.
- `review`: a nonempty list of entries.
- `review_budget`: a positive integer, or `null` to keep the caller's own count.
- `ranking_source`: a leaderboard URL, or `null` to offer only the configured defaults.

Each entry has `agent`, `model`, and `effort`. `null` for `model` or `effort` inherits the agent's own default. If the file is missing or invalid, stop and report the path and error.

## 2. Build the choices

1. **Implementation, per unit.** When `ranking_source` is set, offer up to three rows (Best value, recommended; Lowest cost; Highest capability) per [model proposal](references/model-proposal.md). Otherwise offer the configured entry.
2. **Review models.** A multi-select with the file's entries preselected, plus the proposal's shortlist for the review task. At least one must remain.
3. **Review budget.** The file's value as the default.

Skip any item the user's request already settles.

## 3. Ask and wait

The model question is required input:

1. Show the choice table and the review-model list.
2. End with one plain-text question: "Reply with your pick per unit and the review models, or `defaults`."
3. End your turn. Dispatch only after the user replies.

The file's defaults are not the user's answer. Host rules that prefer making assumptions over asking do not cover this question. Use the host's question tool only when it allows required input; otherwise use plain text as above. Skip the question only when the request names every choice or says "use the defaults".

Apply the answers for this run only. Leave `models.yaml` unchanged unless the user asks to save them.

## 4. Resolve names

For each chosen entry, check the agent's model catalog on the execution host:

- A full provider ID must match exactly. A short name must equal a model's name, as a bare ID or after the provider prefix. No prefix, substring, or "latest" matches.
- No match, or several: ask the user for a full ID.
- Confirm the agent supports the chosen effort.

Never substitute a different agent, model, or effort. If a choice cannot be verified, report it unavailable.

## 5. Dispatch and record

Pass model and effort as real launch options on every dispatch. Naming them in a prompt does not select them.

| Host | Options |
| --- | --- |
| Orca | `orchestration worker-start --agent --model --effort` |
| Codex `spawn_agent` | `model`, `reasoning_effort` |
| Claude Code `Agent` | `model`, `effort` |

Omit an option only for a `null` (inherit) choice. For each dispatch, record the role, the requested agent, model, and effort, and the effective settings from the launch receipt, or "unverified" when the host shows none. A worker's statement about its own model is not evidence.
