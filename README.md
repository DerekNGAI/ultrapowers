# ultrapowers

OpenCode skills, agents, and a bounded review workflow.

## Dual review

`/dual-review` sends the current project change to two independent, read-only
reviewers. The read-only `ultrapowers-judge` primary agent judges every finding,
delegates accepted fixes and checks to OpenCode's built-in `general` subagent,
and returns rejected substantive findings to their originating reviewer.
Reviews stop after three rounds. Nits do not block approval.

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
primary agent's model. The judge uses your normal selected model; optionally
override `agent.ultrapowers-judge.model`. General uses its existing OpenCode
configuration and inherits the calling judge's model if no model is configured
for general. The package does not override general's model, prompt, or permissions.

If migrating from `ultrapowers-build`, move your agent overrides to
`agent.ultrapowers-judge` and update `default_agent` if it names the old agent.

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

Alternatively, select `ultrapowers-judge` as your primary agent and give it a
coding task. It plans the work, delegates implementation and checks to general,
then performs dual review before declaring completion. Preflight must pass
before either implementation or review begins. If general is disabled or its
permissions prevent implementation, the judge reports `INCOMPLETE` with the
blocker.

For CLI use:

```sh
opencode run --command dual-review
```

The judge session shows the reviewer models, round and snapshot, findings, and
accept/reject decisions. OpenCode's child-session navigation lets you inspect
general and each reviewer independently. The judge resumes one general session
per request for implementation, checks, and fixes, and resumes each reviewer's
own session for revised snapshots and rebuttals.

General receives an implementation brief with scope, constraints, expected
workspace state, and required checks. For fixes it receives accepted finding IDs
and the evidence needed to implement them. It returns changed paths, addressed
IDs, check commands and outcomes, and blockers. Detailed implementation reads,
edits, and check output stay in general's session. Full review snapshots remain
in the judge's conversation, so large diffs still use its context. Delegation
reduces implementation context in the judge; it does not guarantee lower total
token usage across all agents.

The final report includes both reviewer verdicts and a finding table showing
fixed issues, explicit withdrawals, remaining disputes, deferred nits, and fixes
that still need review. Overall outcomes are `APPROVED`, `ROUND_LIMIT`,
`INCOMPLETE`, or `NO_CHANGES`. Approval requires both reviewers to cover the
same final snapshot and the required checks to pass.

### Limits and permissions

The shared protocol permits three full reviews and one rebuttal per reviewer in
each round. The package additionally enforces six Task calls per reviewer per
invocation, including resumed sessions, with native step budgets of 80 for the
judge and 30 for each reviewer. General calls do not consume the reviewer
budget. A new explicit judge request or
`/dual-review` invocation starts a new budget; synthetic continuation messages
preserve it. A new request to another agent ends the workflow's implementation
gate. A denied call requires the judge to stop and summarize.

Round sequencing, JSON findings, independence, and decisions are agent
instructions, not a custom scheduler. File and tool restrictions and the Task
call ceiling are enforced by OpenCode permissions and the package hooks.
Reviewers can read, list, glob, and search files. Their shell commands, writes,
delegation, and MCP tools are denied. The judge can inspect files, use read-only
Git commands, and delegate to general and the two reviewers; direct edits and
unlisted tools are denied. General runs checks and applies fixes using its own
configured permissions. All workflow tasks run in the foreground. The hook
blocks implementation after failed preflight and rejects background tasks during
an active workflow. General finishes before a snapshot is captured, and both
reviewers finish before any fixes or checks are delegated. The full protocol is in
[dual-review.md](.opencode/instructions/dual-review.md).

## Committer

Use `/commit` when implementation and validation are complete. Every invocation
starts with OpenCode's native question tool, offering these choices:

| Choice | Result |
| --- | --- |
| Current branch | Create local Conventional Commits on the current branch. No push or PR. |
| PRs without prefix | Create independent branches such as `fix/login-error`, push them, and open draft PRs. |
| PRs with prefix | Ask for an issue prefix, then create branches such as `fix/ZE-1659-login-error`, push them, and open draft PRs. |

The answer authorizes only the selected workflow. `/commit ZE-1659` still asks
for the mode; in prefixed mode, the argument is offered as a suggested prefix.
Prefixes must contain only ASCII letters, digits, and hyphens. The other modes
ignore supplied prefixes. Cancellation or an unavailable question tool stops
the workflow before Git state changes; there is no automatic mode selection.

All modes support any named current branch with an existing commit, including
`main`, `master`, `develop`, `staging`, and feature branches. Current branch mode
works without GitHub access or a remote and stays on that branch as each commit
advances its HEAD. The PR modes use the current branch as their base and require
its SHA to match the freshly fetched origin branch. Missing access or an
unsynchronized base stops those modes before staging changes.

SSH origins can use aliases such as `github-work`. Preflight resolves the
configured hostname with `ssh -G` before verifying the GitHub repository; it
keeps the original origin for fetching and pushing. SSH connection commands
remain denied.

The agent stops on sensitive files, suspected credentials, or changes it cannot
fully inspect. It groups shared-file and dependent changes together. Staged,
unstaged, and non-ignored untracked changes are included; existing staging
boundaries are cleared without discarding file contents. Each group's staged
diff and actual commit are checked, including hook effects.

In PR modes, independent groups each start from the captured base commit. Each
group is committed, pushed, and given a draft PR before the next group starts.
PRs specify the origin repository, head branch, and starting base explicitly.
After success the agent returns to the original base branch. On failure it
reports partial progress while preserving work and created branches. It reports
supplied validation evidence and pending checks; it does not run tests or infer
that an independent branch passed tests from a combined workspace run.

Mode selection, grouping, credential inspection, and state comparisons are agent
instructions, not a custom scheduler or secret scanner. OpenCode enforces the
configured tool and sensitive-file read permissions. **Quit and restart OpenCode
after changing this agent's configuration or prompt.**

## Verification

```sh
npm test
```

The tests in `test/committer.test.js` use Node's built-in test runner and isolated
temporary Git repositories to execute the committer prompt's shell examples.
They check local commits on a feature branch without a remote, independent PR
branches from `develop` and `staging` with and without a prefix, mixed staged and
unstaged edits, untracked files, filenames with spaces, literal commit bodies,
and return to the starting branch. Local bare repositories receive test pushes;
no live GitHub PRs are created. Configuration checks cover the question options,
question permission, command routing, generalized branch permissions, and explicit
PR targets. These tests do not establish that a model follows every instruction.
The resolved command, prompt, question permission, and branch permissions were
also checked with isolated settings on OpenCode 1.18.35.

For an interactive acceptance check, restart OpenCode and invoke `/commit` in a
disposable repository. Confirm the mode question appears on each invocation,
including `/commit ZE-1659`, and that prefixed mode asks for the prefix. Cancel
the question and confirm Git state is unchanged. Choose current branch mode and
confirm local commits are created without a push or PR.

Previous dual-review validation covered judge registration, command routing,
permission configuration, preservation of general overrides, preflight gates,
foreground tasks, and per-reviewer call limits. Provider metadata was supplied
by a test client; no live model calls were made in those checks.
The resolved configuration was also checked with isolated settings on OpenCode
1.18.33: `/dual-review` routes to the judge, the judge cannot edit or run unlisted
shell commands, native general retains write and shell access, and both
reviewers remain read-only.
Automatic template creation and a repeat startup without rewriting the config
were also checked with isolated JSONC settings on OpenCode 1.18.33.
Earlier registration and resolved reviewer permissions were checked with
OpenCode 1.18.33. A live CLI check of the previous implementation confirmed
snapshot capture, two configured-model task launches, and an `INCOMPLETE` verdict
table on provider rejection. The tested
OpenCode free-tier models rejected subagent requests with "OpenCode's free tier
can only be used from within OpenCode"; their successful main-agent calls did not
establish reviewer access. A subsequent check using OpenAI and Anthropic also
ended as `INCOMPLETE` due to region and forbidden-access responses, with no
retries after the first round. The successful delegated implementation and
findings/fix/rebuttal loop still needs verification with models that accept
subagent requests.

For a live acceptance check with two configured models:

1. Prepare a small change with an observable defect and a check reproducing it.
   Run `/dual-review` and confirm both reviewers inspect the same snapshot.
2. Confirm the judge records reasons for its decisions, delegates valid fixes and
   checks to general, waits for completion, verifies the resulting diff, and
   sends the revised snapshot back to both reviewers. Confirm implementation
   follow-ups resume the same general session and reviewers remain independent.
3. If a false positive occurs, confirm the rejection goes only to its owner,
   which withdraws or keeps it with additional evidence. Repeated evidence
   alone must not sustain an objection.
4. Check that nits-only reviews approve, and an unresolved blocker ends at round
   three with a dispute in the final table. A fix after the final review must be
   labeled unverified instead of inheriting an earlier approval.

Passing the loader tests alone does not establish that a chosen model follows
the protocol. Real reviewer output is deliberately not predetermined.
