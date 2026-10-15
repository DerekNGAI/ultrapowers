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

Before each full review, including revised snapshots, the judge copies the same
complete evidence block directly into both reviewer Task prompts. It includes
the snapshot ID, scope, each repository's absolute root/HEAD/status/file hashes,
complete staged and unstaged diffs, full untracked contents labeled by path, and
check commands, results, and limitations. Empty diffs and lists are explicit.
Reviewers do not inherit the judge's conversation and cannot run Git to recover
missing or deleted code. The judge checks that every changed path is covered
before launching either reviewer and reports `INCOMPLETE` if required evidence
is unavailable, restricted, truncated, or too large for either reviewer's context.
Reviewers use file tools for affected callers; the judge verifies Git state.
These handoff checks are agent instructions, not runtime completeness enforcement.

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

## Parallel planning

Use `/parallel-plan <task>` or select `ultrapowers-planner` to split a large task
into plans you can assign to separate implementation sessions:

```text
/parallel-plan Add project invitations with API endpoints, email delivery, and management screens
```

The planner uses your selected model and writes a unique bundle in the active
project. It can write Markdown under `.opencode/plans/` and inspect the project;
source edits, Git writes, and delegation are denied by its default permissions.

```text
.opencode/plans/<job>/
  overview.md
  01-<task>.md
  02-<task>.md
  99-integrate.md
  results/              # Worker reports and patches are added during execution
```

The overview lists file ownership, shared interfaces, dependencies, and waves
of tasks that can run together. Each task file contains its own context, owned
files, prerequisite paths, worktree setup, acceptance criteria, checks, and
handoff instructions. Foundation work finishes before tasks that use it. The
planner uses a sequential plan when there is no safe parallel split.

1. Open the overview and start a fresh **build** session for each ready task.
   Assign it with `Implement the task in @<absolute-task-plan-path>`. The
   planner provides resolved paths and copyable assignment prompts.
2. Each worker creates its own detached Git worktree outside your checkout,
   applies completed prerequisite patches, implements its owned files, and
   runs its checks. Commands and source edits explicitly target that worktree.
   A dependent task exports only its additional changes, so prerequisites are
   not duplicated. Workers save their reports and patches in the original plan
   directory and keep their completed worktrees frozen until integration.
3. Once all tasks are complete, assign `Execute @<absolute-integration-plan-path>`
   to one build session. It assembles the patches in a separate integration
   worktree, completes wiring, and runs the combined checks.
4. Integration applies the tested result to **your original branch and staging
   area**, verifies the staged tree, and removes this job's worker and integration
   worktrees. You review `git diff --cached` and commit the result yourself.
   Plans and recovery patches remain available after cleanup.

Execution requires a named branch with an existing commit and a clean source
and index baseline. Untracked plan artifacts may remain. Existing source changes
are preserved and reported as a setup blocker; the planner does not stash or
commit them. A changed original branch, HEAD, or source state blocks transfer.
Failed checks or unexpected worker files preserve the worktrees for recovery;
cleanup resumes after the work is verified. A partially completed cleanup is
reported as `CLEANUP_PENDING`, not success. Submodule-content changes require a
different handoff and are reported as a planning blocker.

The worker and integration plans use the implementation agent's existing
permissions. Native directory approval may be needed for sibling worktrees.
Assign one session per task and one final integration session. Ownership,
readiness, and dependency checks are agent instructions; this feature does not
automatically launch or schedule workers. Isolated worktrees prevent agents
from overwriting each other's files, while integration checks catch incompatible
behavior across tasks.

**Quit and restart OpenCode to load the planner and command.** When developing
from this checkout, consuming projects can load its `index.js` through a local
plugin path; a plugin pinned to an older Git revision must be updated separately.

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

Git inspection permissions cover command families, including `git diff`,
`git status`, `git rev-parse`, `git log`, and blob/index inspection. Option order
and quoted arguments do not need separate inspection rules. Unexpected shell
commands request native approval; destructive resets, restores, cleaning, branch
deletion, amended commits, hook bypasses, force pushes, and Git configuration
changes remain denied. Skills are available for optional document inspection.
Fetch and push permissions still target origin and the workflow's explicit refs.
The prompt's exact quoted commit heredoc header has an explicit allowance because
native matching includes the message body. Mentioning prohibited flags in that
body does not block a normal commit; flags added to the command remain denied.

Access to directories outside the active project, including separate Git
worktrees, requests native permission approval. Approve the worktree directory
to let the committer perform its allowed Git operations there. A denied required
directory request stops the workflow before it can proceed.

The agent stops on sensitive files, suspected credentials, failed required
inspection, or unexpected state changes. PDFs, images, and other binary assets
are supported: it captures working-file hashes and expected Git blob IDs, then
verifies the staged and committed blobs and modes. Git attributes and clean
filters may make the stored blob differ from the working-file bytes. Deleted
assets must be absent from the index and committed tree. `git diff --no-index`
exit code `1` means files differ and is expected, not a failed preflight.

Binary content inspection is optional. A missing, denied, or unsupported reader
does not block required hash verification. Unreviewed assets are listed as
`Binary contents not reviewed` in the plan, PR description, and final report;
hash checks do not establish document correctness or the absence of embedded
secrets. Required tool denials and mismatched hashes still stop publication.

It prefers the smallest coherent, reviewable commit with one clear purpose. Tests
stay with the behavior they verify, plus configuration and dependencies required
for that step. Local commits may depend on earlier commits in the sequence and
split text changes within the same file, including newly added files. Each
intermediate commit must leave the project working. For example, a prerequisite
refactor with tests can precede implementation with unit tests, then caller
integration with integration tests. Shared files or dependencies alone do not
require one large local commit.

Groups above 400 added plus deleted lines of non-generated text trigger another
attempt to split and an explanation if kept together. This is a review threshold,
not a hard cap. Renames, deletions, binary assets, and generated files stay whole;
dependency manifests and lockfiles stay synchronized.

Staged, unstaged, and non-ignored untracked changes are included; existing staging
boundaries are cleared without discarding file contents. Whole-file groups use
explicit paths; partial local changes use checked `git apply --cached` patches
without editing working files. Only the documented check and apply heredocs are
allowed; other `git apply` commands are denied. Each group's staged diff and actual
commit are checked, including hook effects. Final text blobs must match the captured
change after repository normalization. Combined-workspace tests are not reported
as proof that intermediate commits passed.

In PR modes, shared-file and dependent changes stay together so each group works
independently from the captured base commit. These modes do not create stacked PRs.
Each group is committed, pushed, and given a draft PR before the next group starts.
PRs specify the origin repository, head branch, and starting base explicitly.
After success the agent returns to the original base branch. On failure it
reports partial progress while preserving work and created branches. It reports
supplied validation evidence and pending checks; it does not run tests or infer
that an independent branch passed tests from a combined workspace run.

Commit messages and PR titles/descriptions have no auto-generated labels or
analysis markers. Commit bodies add brief context only when the subject needs it.
PR descriptions use these Markdown headings in order:

```markdown
## What?
## Why?
## How?
## Testing?
## Screenshots (optional)
## Anything Else?
```

Each section uses specific facts in a short paragraph or a few brief bullets,
without repeating explanations or padding the description. Testing lists supplied
checks and results, labels previous workspace checks, and names relevant pending
checks. When no results were supplied, it says `No test results supplied.` once.
Routine Git bookkeeping stays in the final workflow report. Screenshots are omitted
when unavailable; Anything Else contains relevant rollout, rollback, compatibility,
binary inspection limits, or issue references, or `None.` when there are no extras.

Mode selection, grouping, credential inspection, and state comparisons are agent
instructions, not a custom scheduler or secret scanner. OpenCode enforces the
configured tool and sensitive-file read permissions. **Quit and restart OpenCode
after changing this agent's configuration or prompt.**

For local development, point a consuming project's plugin entry at the edited
checkout's `index.js`, for example `file:///absolute/path/to/ultrapowers/index.js`.
A Git plugin reference containing `#<commit>` keeps loading that revision until
the reference is updated. This repository already loads `../index.js` from its
project configuration.

## Verification

```sh
npm ci
npm test
```

`test/parallel-plan.test.js` checks planner/command registration and executes the
Git recipes from the planner prompt in disposable repositories. It covers
independent and dependent workers, new text and binary files, deletions, final
staging without advancing HEAD, worktree cleanup, and refusal to discard changed
or ignored files. It also checks that native OpenCode permissions allow plan
files while denying source edits and Git writes when OpenCode is installed.
These checks do not invoke models or establish that a model always produces a
correct decomposition. For interactive acceptance, run `/parallel-plan` in a
disposable clean repository, assign its ready tasks to separate build sessions,
then run its integration plan and inspect the staged result and worktree list.

The tests in `test/committer.test.js` use Node's built-in test runner and isolated
temporary Git repositories to execute the committer prompt's partial-staging
commands. They split tracked and newly added text files, including filenames with
spaces, into successive dependent commits while preserving the complete working
files. They verify each committed tree and parent, Git line-ending normalization,
the final clean state and blob, and that a mismatched patch changes neither the
index nor working files. When OpenCode is installed, a native debug-tool check also
verifies the cached heredocs are allowed and working-tree patch commands are denied
using isolated settings without external plugins. This check skips when OpenCode
is absent. No live model calls, remote pushes, or GitHub PRs are made; these tests
do not establish that a model chooses good groups or follows every instruction.

For an interactive acceptance check, restart OpenCode and invoke `/commit` in a
disposable repository. Confirm the mode question appears on each invocation,
including `/commit ZE-1659`, and that prefixed mode asks for the prefix. Cancel
the question and confirm Git state is unchanged. Choose current branch mode and
confirm local commits are created without a push or PR.
Include separable edits in one text file and confirm local commits contain only
their planned portions, in dependency order. Include a group over 400 changed
lines and confirm the plan explains any remaining large group. In PR mode,
confirm shared-file and dependent changes stay together in an independent branch.

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

1. Prepare a disposable repository with a deleted tracked file, a staged-only
   change, and a non-ignored untracked file. Seed an observable defect and a check
   reproducing it, then run `/dual-review`. Inspect both child sessions: each Task
   prompt must contain the same complete evidence, including the removed code
   and untracked contents. Both reviewers should identify the defect using that
   evidence and permitted file tools, without trying to run Git or reconstruct
   missing diffs. Missing evidence must yield specific incomplete coverage.
2. Confirm the judge records reasons for its decisions, delegates valid fixes and
   checks to general, waits for completion, verifies the resulting diff, and
   sends the complete revised snapshot back to both reviewers. Confirm implementation
   follow-ups resume the same general session and reviewers remain independent.
3. If a false positive occurs, confirm the rejection goes only to its owner,
   which withdraws or keeps it with additional evidence. Repeated evidence
   alone must not sustain an objection.
4. Check that nits-only reviews approve, and an unresolved blocker ends at round
   three with a dispute in the final table. A fix after the final review must be
   labeled unverified instead of inheriting an earlier approval. Confirm the judge
   rechecks Git state before approval.

Passing the loader tests alone does not establish that a chosen model follows
the protocol. Real reviewer output is deliberately not predetermined.
