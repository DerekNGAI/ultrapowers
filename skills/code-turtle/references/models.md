# Review model policy

Resolve models after preparing a nonempty diff and before dispatching any review agent. Model selection is orchestration metadata; keep it separate from the reviewed source and candidate evidence.

## Select once

Use this precedence, field by field:

1. Explicit model, effort, or runtime choices in the user's request.
2. The enclosing worker brief's resolved `MODEL_POLICY`, when supplied.
3. [The shared config](../../orca-poteto/models.yaml), resolved relative to this file after following the skill directory's symlinks.

For a standalone run, read the config schema and exact-name resolution rules in the **Model configuration** section of [orca-poteto](../../orca-poteto/SKILL.md). Reuse that data contract without starting its coordinator or implementation workflow. Missing or invalid configuration is an error before dispatch. The `agent` field selects the runtime; a native subagent model override cannot change runtimes.

Map roles as follows:

| Role | Policy entry |
| --- | --- |
| Summarizer, in full mode | `implementation`, as a non-review helper |
| Bug hunter and security finder | `review` entries in order, cycling if needed |
| Each fresh verifier | `review`, preferring an entry different from its finder when available |

The small-mode summary is written by the parent and needs no summarizer selection. An entry may explicitly inherit with `model: null` or `effort: null`; record that choice as inherited. An omitted role setting or unavailable model is not permission to inherit.

When an enclosing brief supplies a resolved policy, reuse its resolved IDs and efforts without reopening the picker or loading another config copy. Otherwise enumerate the current host's native subagent catalog, supported efforts, runtime, and configured defaults. For a choice on another runtime, use an available authorized dispatch route for that runtime or report the selection unavailable; never silently switch the `agent` field. Resolve each distinct choice once using the shared exact-name rules.

For unsettled standalone choices, reuse [model proposal](../../orca-poteto/references/model-proposal.md) with review roles as its units. Its default is the mapped entry above; its candidate catalog is the dispatch routes this host can actually launch, rather than requiring Orca. Show the summarizer and review selections together and ask once before dispatch. Keep an explicitly supplied review list fixed. A request to use defaults skips suggestions and the question. Explicit choices skip the question for the roles they settle. Preserve run-only choices without editing the shared config.

Keep the standalone skill's full reviewer count unless the user explicitly sets `review_budget`. Inside a worker, honor the enclosing brief's remaining `REVIEW_BUDGET`; the shared config's per-worker budget does not cap a standalone review. Each finder and verifier consumes one reviewer slot; the summarizer does not. Apply the budget in workflow order: required finders first, then verifiers for valid candidates in severity order. Preserve the separate finder and verifier stages. If an explicit or enclosing budget cannot cover them, report incomplete coverage and omit claims without an independent verdict. A user can request `review_budget: null` to retain the full count. Do not combine a finder with its verifier to fit a budget.

Done when every required role has an available resolved selection, an explicit inheritance choice, or a reported coverage limitation, and all unsettled choices have been answered.

## Dispatch with the selected options

Load each role's definition from `../../../agents/turtle-*.md` relative to this reference, following directory symlinks. Preserve its read-only behavior. Use fresh agents with only the role instructions and the neutral review pointers. A verifier also receives only `{file, line, claim}` from one candidate. Selecting another model never grants it the parent's transcript.

Pass the resolved model and effort as actual tool options on **every** finder, summarizer, and verifier invocation. Mentioning them in a prompt or choosing a role type does not select the model. Plugin role frontmatter is a fallback for direct use; this run's policy overrides it.

| Host | Invocation |
| --- | --- |
| Codex with `spawn_agent` | Use `agent_type: "turtle-…"`, `fork_turns: "none"`, `model: <resolved ID>`, and `reasoning_effort: <resolved effort>`. Put the role instructions and minimal pointers in `message`. If a role type is unregistered, use the host's general agent with that role's read-only instructions. |
| Claude Code with `Agent` | Use `subagent_type: "ultrapowers:turtle-…"`, `model: <supported model ID>`, `effort: <supported effort>`, and a minimal `prompt`; use a non-fork agent. Per-invocation effort requires Claude Code 2.1.292 or newer. |
| Another host | Use its independent subagent tool with its verified model and effort options and the same minimal role brief. |

Omit a model or effort option only for that field's explicit `null` inheritance choice. Inspect the live tool schema before invocation. If the tool cannot honor a selected runtime, model, effort, or fresh-context requirement, report that role unavailable instead of dropping the option. If a role's fixed frontmatter would override an explicit inheritance choice, use a general agent with the role instructions and verified inheritance semantics, or report it unavailable. Do not change global settings or installed role definitions.

Save a `model-dispatches.json` array beside `context.json`. For each attempted dispatch record the role, candidate file/line for a verifier, selected runtime, resolved model and effort (including explicit inheritance), actual model/effort/context tool options, returned agent ID or error, and effective settings when the host exposes them. Record the attempt even if the launch fails. Save no finder reasoning in a verifier's prompt.

Compare requested and effective settings when metadata is available. A conflicting effective setting is a failed role check. When the host exposes only the request and successful launch, label the effective settings **unverified**; a child's statement about its own model is not runtime evidence.

Include each role's requested model and effort, inheritance, failures, and effective-setting evidence or its absence in the final coverage note. A failed required dispatch makes the review incomplete. Unavailable effective metadata limits the model audit; it does not establish a mismatch.

Sources for Claude Code's model and per-invocation effort behavior: [subagents](https://code.claude.com/docs/en/sub-agents). The live host's tool schema is authoritative for its available options.
