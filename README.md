# ultrapowers

Agent skills for code review, multi-agent work coordinated by Orca, and atomic commits. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format. The repository root is also a Claude Code plugin named `ultrapowers`.

## Skills

- `code-turtle`. Review someone else's change with a plain-language summary first, followed by independently checked issues and comments ready to paste. Slow and steady: every finding is verified before you see it.
- `orca-poteto`. An Orca coordinator assigns bounded tasks to separate poteto worker sessions. Each worker selects its poteto playbook and owns implementation, verification, and prescribed reviews. Each worker gets explicit commit, push, and PR permissions. The skill never grants merge. When a run settles with nothing waiting on the user, the coordinator removes the worktrees it created, keeps the deliverable branches, and switches its checkout back to the original branch. Status: a recommended adaptation, not a tested integration.
- `model-selector`. Shared configuration, verified model resolution, ranking, and approval for callers. It selects choices before launch; callers keep their own agent lifecycle.
- `commit-style`. Atomic commits with [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) messages. The agent reads the repository's own convention first, splits the change into atomic commits, stages by path, verifies, and writes a typed header with a body that explains why. It needs neither Orca nor poteto.

## Requirements

For `code-turtle`:

- Claude Code with plugin skills and subagents. The plugin commands below are verified with Claude Code 2.1.326.
- Git and Python 3.12 or newer for saved diffs and source snapshots.
- GitHub CLI (`gh`) for PR-number targets. The PR's base and head objects must already exist locally.

For `orca-poteto`:

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill.

The coordinator loads the installed orchestration skill. Each worker loads the installed poteto-mode skill through an absolute path in its brief. The coordinator reads acceptance evidence and checks integration between deliverables without repeating the worker's engineering phases. Additional engineering review needs a worker request, a user request, or a concrete integration risk.

The wrapper leaves both underlying skills and their standalone settings unchanged. Updates to their installed copies apply on the next run.

## Configure agents and models

Edit [`skills/model-selector/models.json`](skills/model-selector/models.json). This is the only model config. Each role entry has `agent`, `model`, and `effort`. Use complete model names, full IDs, or verified runtime aliases. JSON `null` inherits the corresponding runtime or model default: an inherited model keeps the session effort, while an explicit model with null effort uses that model's default. Missing fields, duplicate keys, unknown fields, and empty values stop selection.

The selector resolves names against the selected runtime's available models and verified launch adapters. It prefers the configured provider when unambiguous and asks for a full ID when it cannot select one match. The `agent` field fixes the runtime; model providers do not change it. An unsupported runtime, model, or effort stops dispatch. Each saved policy records requested, resolved, inherited, and effective choices. Requested flags alone do not prove the effective choice.

The `code-turtle` profile provides `summarizer`, `finder`, and `verifier` roles. Defaults preserve Haiku summarization and the session model/effort for finding and verifying. The finder choice applies to both correctness and security finders. `review_budget` stays `null` because every valid claim needs an independent verifier. Selection happens before review; it shows configuration without exposing findings. Ask for specific roles or say “use defaults” to skip the approval question. For example: “Review this branch; use defaults, except verifier model `remote-magpie/claude/claude-sonnet-5-5` at `max`.” That ID is a host-specific example and must exist in the execution host's catalog.

Claude Code's Agent tool supports aliases and inheritance. Full IDs or efforts that tool cannot apply use a separate Claude CLI process with a session-only role definition, read-only tools, and actual request/response checks. This route needs no Orca. Native reviews need accessible effective child evidence; for request auditing, start Claude Code with `OTEL_LOG_RAW_API_BODIES=file:/absolute/private/review-trace`. See [launch adapters](skills/code-turtle/references/launch-adapters.md) for discovery and audit commands. The caller stops if neither route can verify the choice. It never patches installed agents or settings.

The `orca-poteto` profile provides `implementation`, `review`, `review_budget`, and `ranking_source`.

At the start of a run the coordinator splits the request into units and proposes an implementation model for each one. It reads the models the host can launch, looks them up on the leaderboard at `ranking_source`, and rates each unit's demand: a hard unit gets the top-ranked model, an ordinary unit gets the `implementation` entry, and a mechanical unit gets a cheaper choice. You approve or edit the table once before anything is dispatched. The ranking is saved at `~/.cache/model-selector/model-ranking.md` and fetched again when the available models change or you ask for a refresh. Set `ranking_source` to `null`, or tell the run to use the defaults, to run every unit on the `implementation` entry. Reviewer models stay the same for the whole run.

Explicit instructions for a run override individual fields without editing the file. The skill reads the config beside its own installed `SKILL.md`, not from the project being worked on.

## Install

### Claude Code plugin

For one session, load the local repository without changing installed plugins or settings:

```sh
claude --plugin-dir /absolute/path/to/ultrapowers
```

For a persistent installation in the current project, register this repository's local marketplace, then install its root plugin:

```sh
claude plugin marketplace add /absolute/path/to/ultrapowers --scope local
claude plugin install ultrapowers@ultrapowers --scope local
```

Start a new Claude Code session after installation. `local` scope saves enablement in the current project's `.claude/settings.local.json`. Use `project` scope for shared project settings or `user` scope for all projects. A local marketplace reads this plugin's files directly; restart the session or run `/reload-plugins` after edits. Hosted marketplace installs use cached copies.

You can also install the published repository from inside Claude Code after the plugin commit is available there:

```text
/plugin install ultrapowers --marketplace DerekNGAI/ultrapowers
```

The plugin exposes `/ultrapowers:code-turtle`, `/ultrapowers:orca-poteto`, `/ultrapowers:model-selector`, and `/ultrapowers:commit-style`. Its review agents are `ultrapowers:turtle-summarizer`, `ultrapowers:turtle-bug-hunter`, `ultrapowers:turtle-security`, and `ultrapowers:turtle-verifier`. The plugin adds no hooks or shared model settings. The summarizer uses Haiku; the other review agents inherit the session model.

Validate a local copy with `claude plugin validate /absolute/path/to/ultrapowers`. See the official [plugin component reference](https://code.claude.com/docs/en/plugins/components) and [subagent reference](https://code.claude.com/docs/en/sub-agents) for supported metadata.

From the plugin repository, run the review and adapter checks with `python3 -B -m unittest discover -s skills/code-turtle/tests -v`. Run shared resolution checks with `python3 -B -m unittest discover -s skills/model-selector/tests -v`.

### Directory links for other agents

Link the whole skill directory into the skill folder of every agent that should see it. Directory links keep the instructions and configuration together and share one editable config:

```sh
ln -s "$PWD/skills/model-selector" ~/.agents/skills/model-selector
ln -s "$PWD/skills/orca-poteto" ~/.agents/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.codex/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.claude/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.grok/skills/orca-poteto
```

The callers resolve sibling dependencies from the real skill path, following directory links. Copy installations must include `model-selector` beside `orca-poteto` and `code-turtle`. A missing dependency stops dispatch with its absolute path. Link `model-selector` into each host for direct discovery as needed.

Link `commit-style` the same way, for example `ln -s "$PWD/skills/commit-style" ~/.claude/skills/commit-style`.

For `code-turtle`, link its whole directory, for example `ln -s "$PWD/skills/code-turtle" ~/.agents/skills/code-turtle`. Its role definitions remain at this repository's `agents/turtle-*.md`. A copied installation must preserve that layout: `skills/code-turtle`, `skills/model-selector`, and `agents` under one root. A host using the linked skill must support independent subagents and load those definitions with read-only tools. The Claude Code plugin packages them automatically. A skill link alone does not register Claude Code plugin agents or namespaced commands.

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update the whole skill directory, including `SKILL.md`, scripts, and references. Move existing Orca model choices into `models.json` under `orca-poteto.roles`, with the budget and ranking source beside `roles`. Remove the old `orca-poteto/models.yaml`; there is no second config or fallback path. Preserve local choices when updating copied installations. Start a fresh coordinator conversation to use the updated instructions without previously loaded poteto instructions.

## Review a change

In a repository you want to review, run one of these commands:

```text
/ultrapowers:code-turtle 123
/ultrapowers:code-turtle feature-branch
/ultrapowers:code-turtle 6a93ac4
/ultrapowers:code-turtle main...feature-branch
/ultrapowers:code-turtle path:src/parser.py
```

With no target, the skill reviews tracked staged and unstaged changes against `HEAD`. A path restricts those changes. Untracked files are excluded. Use `path:`, `branch:`, or `commit:` when a name is ambiguous. Branch review uses the merge base with `origin/HEAD`, `main`, or `master`; use an explicit range for another base. Commit review compares the commit with its first parent. PR review uses the merge base of the PR's base and head objects. The skill never fetches or checks out a ref.

The review saves its diff and source snapshots outside the repository and passes file pointers to each agent. It resolves the approved role models before dispatch. Below 50 changed lines, one finder checks correctness and security, then independent verifiers check its claims. Larger diffs run a summarizer, a bug hunter, and a security finder in parallel before verification. The summarizer defaults to Haiku. Binary changes and unavailable submodule content select the full path and appear as coverage limits.

The summary comes first. Every issue has `file`, `line`, `severity`, `claim`, `failure_scenario`, `comment`, and `verdict`. Scenarios include a concrete input or state, the wrong result, and a quoted source line. Confirmed issues have independent static evidence; agents have read-only file tools and do not execute reproductions. Plausible issues state what remains unverified. Rejected claims are dropped. A finalization script validates the issue schema, ranks the results, caps them at ten, and saves `findings.json` and `review.md`. The orchestrator merges findings about the same root cause before that check. A clean review can contain zero issues.

Comments use Conventional Comments prefixes: `issue (blocking):`, `suggestion:`, or `question:`. Paste them into your review yourself. Version 1 never posts comments to GitHub. If an agent or verifier is unavailable, the review states the limitation and remains incomplete.

Inspired by CodeRabbit and the tortoise-and-hare story.
