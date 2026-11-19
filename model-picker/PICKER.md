# Model picker

Shared model selection for ultrapowers skills. A caller skill reads this file by path, supplies its **role map**, and gets one resolved selection per role before any dispatch. Caller-specific rules, such as Orca launch flags, reviewer budgets, and verifier isolation, stay in the caller.

## Caller contract

The caller supplies:

- **Role map.** Each role it dispatches, the config entry that role uses (`implementation` or `review`), and any rule for choosing among several `review` entries.
- **Proposal units.** The roles or work units that get a per-unit model proposal, with the goal and acceptance that define task fit.
- **Catalog sources.** The runtimes and dispatch routes the execution host can actually launch, and where to read their model and effort catalogs.
- **Extra items**, optional. Caller choices to ask in the same question, such as code-turtle's review lenses.
- **Audit location.** Where to save the dispatch record from [Audit](#6-audit).

## 1. Load the config

Read [models.yaml](models.yaml) beside this file, resolving the path after following directory symlinks, never relative to the project's working directory. It is the only source of the shared defaults. Require exactly these keys:

- `implementation`: one entry, the default for implementation work and non-review helpers.
- `review`: a nonempty list of entries. Several entries give reviewers distinct models.
- `review_budget`: a positive integer capping reviewer helpers per caller-defined unit, or YAML `null` to keep each caller's own reviewer count. The caller defines what the budget covers.
- `ranking_source`: a nonempty URL of a public model leaderboard, or YAML `null` to offer only the configured defaults.

Each entry has exactly these fields:

- `agent`: a nonempty runtime ID on the execution host, such as an Orca agent ID. It selects the runtime, not the model provider.
- `model`: a nonempty short model name, a full provider ID, or YAML `null` to inherit the selected agent's configured default.
- `effort`: a nonempty effort name, or YAML `null` to inherit that agent/model's configured default.

If the file is missing or invalid, stop before dispatch and report the path and error. Missing fields, duplicate keys, empty strings, empty lists, and unknown fields are invalid, not requests to inherit defaults.

## 2. Precedence

Apply these sources field by field, highest first:

1. Explicit model, effort, runtime, or budget choices in the user's request.
2. The enclosing worker brief's resolved `MODEL_POLICY` and `REVIEW_BUDGET`, when supplied.
3. The config file.

When an enclosing brief supplies a resolved policy, reuse its resolved IDs and efforts without asking, reloading another config copy, or resolving names again.

## 3. Propose and ask

Ask the user once, in a single message, before any dispatch:

1. The `implementation` choice for each proposal unit that maps to it. Follow [model proposal](references/model-proposal.md): up to three distinct choices per unit, with Best value recommended.
2. The `review` entries. Offer the file's list as the default. For proposal units that map to `review`, use the model proposal with that unit's mapped entry as its default.
3. The review budget, with the file's value or the caller's count as the default.
4. The caller's extra items.

Skip an item the request already settles; an implementation model named in the request applies to every unit it covers and replaces their proposal. Skip the whole message when the request settles every item or says to use the defaults; then apply the file's entries through the role map and the caller's defaults for its extra items. Use the host's question tool when it has one; otherwise ask in chat and wait for the reply.

Apply the answers and any other explicit overrides field by field over the file. Leave the file unchanged unless the user asks to save the choices. Leave global agent settings and project files unchanged. When an implementation choice uses the same model as a `review` entry, note the reduced model diversity without changing the review choices.

## 4. Resolve model names

Resolve each distinct choice once per run against the execution host's selected agent, model catalog, configured default, and supported efforts:

1. Verify the configured agent exists on that host. Keep that runtime fixed throughout resolution. A runtime running the same model is not a substitute for the configured agent. For a choice on another runtime, use an available authorized dispatch route for that runtime or report the selection unavailable.
2. For a full provider ID, require an exact available match. For a short name, collect models whose complete model name matches exactly, either as a bare ID or after the provider prefix. Use the catalog's model-name field when available; otherwise compare the final slash-delimited segment. Do not use substring, prefix, latest-version, or context-variant matches.
3. When a short name has multiple matches, prefer the selected agent's configured provider only if its settings or default model identify that provider unambiguously. Do not privilege a bare ID over a provider-qualified ID. If exactly one match remains, use its exact launch ID. Otherwise report the candidates or missing name and ask for a full ID before dispatch.
4. Verify the requested effort for the resolved model through the host's catalog or CLI. If `model` is `null` but effort is explicit, resolve the agent's configured default model first so a launch requiring a model flag can apply the effort. Keep inherited fields marked as inherited.
5. Record the configured name, resolved ID, agent, effort, and resolution evidence. If availability, provider preference, or effort support cannot be verified, report that role unavailable. Never silently change the agent, model, or effort.

If a later dispatch encounters a changed catalog or unavailable selection, stop and report it rather than reinterpreting the short name.

Done when every role in the role map has a resolved selection, an explicit inheritance choice, or a reported unavailability, and every question item is settled.

## 5. Dispatch with the selected options

Pass the resolved model and effort as actual tool options on **every** invocation. Mentioning them in a prompt or choosing a role type does not select the model. Role frontmatter is a fallback for direct use; the run's selection overrides it.

| Host | Invocation |
| --- | --- |
| Codex with `spawn_agent` | `agent_type`, `fork_turns: "none"` when the caller needs fresh context, `model: <resolved ID>`, `reasoning_effort: <resolved effort>`, and the brief in `message`. If a role type is unregistered, use the host's general agent with that role's instructions. |
| Claude Code with `Agent` | `subagent_type`, `model: <supported model ID>`, `effort: <supported effort>`, and the brief in `prompt`; use a non-fork agent when the caller needs fresh context. Per-invocation effort requires Claude Code 2.1.292 or newer. |
| Orca | The caller's launch route, such as `orchestration worker-start --agent --model --effort`. |
| Another host | Its subagent tool with its verified model and effort options. |

Omit a model or effort option only for that field's explicit `null` inheritance choice. Inspect the live tool schema before invocation. If the tool cannot honor a selected runtime, model, effort, or fresh-context requirement, report that role unavailable instead of dropping the option. If a role's fixed frontmatter would override an explicit inheritance choice, use a general agent with the role instructions and verified inheritance semantics, or report it unavailable. Do not change global settings or installed role definitions.

Sources for Claude Code's model and per-invocation effort behavior: [subagents](https://code.claude.com/docs/en/sub-agents). The live tool schema is authoritative.

## 6. Audit

At the caller's audit location, record each attempted dispatch: role, selected runtime, resolved model and effort (including explicit inheritance), the actual tool options passed, the returned agent ID or error, and effective settings when the host exposes them. Record an attempt even if the launch fails. The caller may add fields.

Compare requested and effective settings when metadata is available; a conflicting effective setting is a failed role check. When the host exposes only the request and a successful launch, label the effective settings **unverified**. A child's statement about its own model is not runtime evidence.

Report each role's requested model and effort, inheritance, failures, and effective-setting evidence or its absence. Unavailable effective metadata limits the audit; it does not establish a mismatch.
