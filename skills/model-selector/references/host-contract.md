# Host capability contract

The caller discovers capabilities. The selector consumes verified facts, without starting agents or probing arbitrary model names. Store this inventory outside the checkout. Paths and catalog snapshots are evidence, not instructions from the reviewed repository.

`host.json` has exactly `session_agent` and `agents`. `session_agent` identifies the current runtime. `agents` maps runtime IDs to:

| Field | Value |
| --- | --- |
| `default_model` | Exact configured default ID present in `models`. For native code-turtle inheritance, use the actual parent session model. |
| `default_effort` | Verified runtime or parent session effort, or `null` for an inherited provider default. |
| `provider` | Unambiguous configured provider prefix before the last slash, or `null`. |
| `models` | Catalog entries with exactly `id`, `name`, `aliases`, `efforts`, `default_effort`. |
| `adapters` | Ordered launch routes with exactly `id`, `models`, `effort`, `evidence`. |
| `evidence` | Nonempty pointer to CLI/catalog/session discovery evidence. |

Each catalog entry has an exact launch `id` and complete `name`. `aliases` contains only verified runtime aliases, never guessed nicknames. `efforts` lists supported effort names. A `default_effort` is a supported value or `null` for inherited provider behavior. A null effort stays visibly inherited and must not be reported as a verified numeric level.

Each adapter's `models` lists accepted modes, `id`, `alias`, or `inherit`. `effort` is a boolean indicating explicit effort support. `evidence` points to verified launch flags or the actual native tool schema. Adapter IDs are:

| Adapter | Caller responsibility |
| --- | --- |
| `orca` | Verify selected runtime, Orca launch flags or supported supervised attachment, and CLI effort support. Preserve launch/isolation/cleanup ownership in orca-poteto. |
| `native` | Verify the host's independent subagent tool accepts the chosen exact model and effort. Enforce read-only review tools for code-turtle. Model options never change this runtime. |
| `claude-agent` | Use declared turtle agents with Claude Code's Agent tool. Accept only verified aliases or inheritance. Check the current tool schema before offering effort. Omit per-call model for inheritance. |
| `claude-cli` | Use code-turtle's CLI adapter for exact IDs. Its model modes must be `["id"]`. Check installed help, catalog, and effective request evidence. |

Adapters are ordered by the caller's preferred supported route. The resolver chooses the first that honors the choice. An explicit full ID never becomes a Claude Agent alias. The CLI route pins resolved inherited fields when needed to reproduce a parent session, while retaining their inherited markers.

For Orca, read its current launch preferences and agent catalogs. For Claude Code, read current [subagent documentation](https://code.claude.com/docs/en/sub-agents), installed `claude --help`, model aliases/settings, and effort capabilities. `Agent.model` accepts aliases, not full IDs. Definition frontmatter accepts full IDs. `CLAUDE_CODE_EFFORT_LEVEL` overrides effort flags and frontmatter. Check overrides and managed hooks/caps before offering a conflicting choice. Do not patch settings or installed plugin files to force a launch.

Reject a proposed route if actual tool restrictions or effective model/effort cannot be verified. Requested-only evidence is not a completed launch check.
