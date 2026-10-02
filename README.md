# ultrapowers

OpenCode skills, agents, and a bounded review workflow.

## Dual review

`/dual-review` sends the current project change to two independent, read-only
reviewers. The primary agent judges every finding, fixes accepted issues, and
returns rejected substantive findings to their originating reviewer. Reviews
stop after three rounds. Nits do not block approval.

### Setup

In another project, add `ultrapowers` to your existing OpenCode `plugin` list.
Use the package version or Git package spec you normally install. This repo's
`.opencode/opencode.json` already loads its local `index.js`.

On startup, the plugin adds missing reviewer templates to your global OpenCode
config. It uses an existing `~/.config/opencode/opencode.jsonc` first, then
`opencode.json`, then the legacy `config.json`; if none exists, it creates
`opencode.json`. When `XDG_CONFIG_HOME` is set to an absolute path, the directory
is `$XDG_CONFIG_HOME/opencode` instead.

The saved entries start with blank model IDs:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "ultrapowers-reviewer-a": { "mode": "subagent", "model": "" },
    "ultrapowers-reviewer-b": { "mode": "subagent", "model": "" }
  }
}
```

Run `opencode models` and replace both blank values with connected
`provider/model` IDs, then quit and restart OpenCode. The plugin supplies the
reviewer prompts and read-only permissions. You can also override the model IDs
in a project's OpenCode config.

Template creation preserves existing models and agent settings, JSONC comments,
config references, file permissions, and symlinks. Existing choices in another
global config file are respected. Once the fields exist, startup does not
rewrite the file. Setup failures are logged as warnings and included in the
preflight setup message when reviewer models are missing.

Each model must support tool calls and have a different `family` in OpenCode's
model metadata. Models may be served by the same provider, such as a gateway
hosting multiple families. Two provider names alone do not establish diversity.
For custom models without family metadata, add the known family in the native
provider configuration alongside the model's other settings:

```json
{
  "provider": {
    "my-gateway": {
      "models": {
        "my-model": { "family": "actual-model-family" }
      }
    }
  }
}
```

The workflow preflights availability and model families before starting. Unset
reviewer models produce an `INCOMPLETE` setup report instead of inheriting the
primary agent's model. The primary agent uses your normal selected model; optionally
override `agent.ultrapowers-build.model` as well.

**Quit and restart OpenCode after changing configuration, prompts, or model
settings.** A running session keeps its loaded configuration.

### Run

In OpenCode, use:

```text
/dual-review
```

You can append review focus, for example `/dual-review focus on error handling`.
The command reviews staged, unstaged, and non-ignored untracked changes. If
there are no changes, it returns `NO_CHANGES`.

Alternatively, select `ultrapowers-build` as your primary agent and give it a
coding task. It implements the change, runs checks, and performs dual review
before declaring completion. It delegates only critique to the two reviewers.

For CLI use:

```sh
opencode run --command dual-review
```

The main session shows the reviewer models, round and snapshot, findings, and
accept/reject decisions. OpenCode's child-session navigation lets you inspect
each reviewer independently. Follow-up calls resume each reviewer's own session.

The final report includes both reviewer verdicts and a finding table showing
fixed issues, explicit withdrawals, remaining disputes, deferred nits, and fixes
that still need review. Overall outcomes are `APPROVED`, `ROUND_LIMIT`,
`INCOMPLETE`, or `NO_CHANGES`. Approval requires both reviewers to cover the
same final snapshot and the required checks to pass.

### Limits and permissions

The shared protocol permits three full reviews and one rebuttal per reviewer in
each round. The package additionally enforces six Task calls per reviewer per
invocation, including resumed sessions, with native step budgets of 80 for the
primary agent and 30 for each reviewer. A new explicit primary-agent request or
`/dual-review` invocation starts a new budget; synthetic continuation messages
preserve it. A denied call requires the main agent to stop and summarize.

Round sequencing, JSON findings, independence, and decisions are agent
instructions, not a custom scheduler. File and tool restrictions and the Task
call ceiling are enforced by OpenCode permissions and the package hooks.
Reviewers can read, list, glob, and search files. Shell commands, writes,
delegation, and MCP tools are denied. Only the main agent runs checks and applies
fixes. The full protocol is in
[dual-review.md](.opencode/instructions/dual-review.md).

## Verification

```sh
npm test
```

The tests use isolated temporary config directories and Node's built-in test
runner to check automatic templates, JSONC preservation, repeated startup,
config failures, symlinks, package registration, local overrides, model
preflight, and per-reviewer call limits.
Automatic template creation and a repeat startup without rewriting the config
were also checked with isolated JSONC settings on OpenCode 1.18.33.
Registration and resolved reviewer permissions were checked with OpenCode
1.18.33. A live CLI check confirmed snapshot capture, two configured-model task
launches, and an `INCOMPLETE` verdict table on provider rejection. The tested
OpenCode free-tier models rejected subagent requests with "OpenCode's free tier
can only be used from within OpenCode"; their successful main-agent calls did not
establish reviewer access. A subsequent check using OpenAI and Anthropic also
ended as `INCOMPLETE` due to region and forbidden-access responses, with no
retries after the first round. The successful findings/fix/rebuttal loop still
needs verification with models that accept subagent requests.

For a live acceptance check with two configured models:

1. Prepare a small change with an observable defect and a check reproducing it.
   Run `/dual-review` and confirm both reviewers inspect the same snapshot.
2. Confirm the main agent records reasons for its decisions, fixes valid issues,
   runs the check, and sends the revised change back to both reviewers.
3. If a false positive occurs, confirm the rejection goes only to its owner,
   which withdraws or keeps it with additional evidence. Repeated evidence
   alone must not sustain an objection.
4. Check that nits-only reviews approve, and an unresolved blocker ends at round
   three with a dispute in the final table. A fix after the final review must be
   labeled unverified instead of inheriting an earlier approval.

Passing the loader tests alone does not establish that a chosen model follows
the protocol. Real reviewer output is deliberately not predetermined.
