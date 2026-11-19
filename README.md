# ultrapowers

Agent skills for code review, multi-agent work coordinated by Orca, and atomic commits. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format. The repository root is also a Claude Code plugin named `ultrapowers`.

## Skills

- `code-turtle`. Review someone else's change with a plain-language summary first, followed by independently checked issues and comments ready to paste. Slow and steady: every finding is verified before you see it.
- `orca-poteto`. An Orca coordinator assigns bounded tasks to separate poteto worker sessions. Each worker selects its poteto playbook and owns implementation, verification, and prescribed reviews. Each worker gets explicit commit, push, and PR permissions. The skill never grants merge. When a run settles with nothing waiting on the user, the coordinator removes the worktrees it created, keeps the deliverable branches, and switches its checkout back to the original branch. Status: a recommended adaptation, not a tested integration.
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

`code-turtle` and `orca-poteto` share one model picker in [`model-picker/`](model-picker/PICKER.md). Edit [`model-picker/models.yaml`](model-picker/models.yaml). Each role has an `agent`, `model`, and `effort`. Use short model names or full provider IDs. Set `model` or `effort` to YAML `null` to inherit the selected agent's configured default.

The picker resolves short names against that agent's available models on the execution host. It prefers the agent's configured provider when unambiguous and asks for a full ID when it cannot select one match. The `agent` field fixes the runtime, so a model choice cannot silently switch reviewers to another agent.

Before dispatch, the picker asks one question. It offers up to three distinct model choices per unit: **Best value** (recommended), **Lowest cost** that meets the task's needs, and **Highest capability**. The table compares task-relevant capability evidence, supported effort, and input/output token prices with units, sources, and dates. Hard work does not automatically select the most expensive model or maximum effort. Duplicate choices share one row; unavailable evidence stays unknown. You choose or edit one row per unit before dispatch. Explicit model choices and requests to use defaults bypass the suggestions they settle. Reviewer models stay the same for the whole run. Each calling skill adds its own role map and can add its own items to the question.

Capability and pricing evidence is saved at `~/.cache/ultrapowers/model-ranking.md` and refreshed when the source or candidate coverage changes, the UTC date changes, or you ask. Price comparisons use the selected provider's published billing terms; public API prices may differ from your actual charges. A stated input/output mix supports comparisons when rates cross. When capability data is unavailable or `ranking_source` is `null`, the picker offers the configured default. When prices are unavailable, it shows capability alternatives without claiming a value or cost winner.

Explicit instructions for a run override individual fields without editing the file. The picker reads the config beside its own `PICKER.md`, not from the project being worked on.

In `code-turtle`, standalone reviews offer model choices before dispatch, unless your request settles them or asks to use defaults. Bug hunters, security finders, and verifiers use `review`; the full-mode summarizer uses `implementation`. Inside an `orca-poteto` worker, turtle reuses the brief's resolved policy and remaining reviewer budget. Standalone reviews retain their full reviewer count unless you explicitly set a budget. Each launch passes the selected model and effort explicitly and records the requested settings and any available effective settings. See [review model policy](skills/code-turtle/references/models.md).

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

The plugin exposes `/ultrapowers:code-turtle`, `/ultrapowers:orca-poteto`, and `/ultrapowers:commit-style`. Its review agents are `ultrapowers:turtle-summarizer`, `ultrapowers:turtle-bug-hunter`, `ultrapowers:turtle-security`, `ultrapowers:turtle-data`, `ultrapowers:turtle-performance`, `ultrapowers:turtle-design`, `ultrapowers:turtle-verifier`, and `ultrapowers:turtle-second-opinion`. The plugin adds no hooks or global model settings. Turtle's resolved per-run policy overrides the role defaults. When invoked directly outside turtle, the summarizer defaults to Haiku and the other review agents inherit the session model.

Validate a local copy with `claude plugin validate /absolute/path/to/ultrapowers`. See the official [plugin component reference](https://code.claude.com/docs/en/plugins/components) and [subagent reference](https://code.claude.com/docs/en/sub-agents) for supported metadata.

From the plugin repository, check diff preparation and final output with `python3 -B -m unittest discover -s skills/code-turtle/tests -v`. Model-picker changes can be replayed against the fictional [behavioral scenarios](model-picker/tests/model-proposal-cases.json); give an evaluator only the inputs, then assess its choices against the checks.

Replay [model-policy scenarios](skills/code-turtle/tests/model-policy-cases.json) by giving an independent evaluator only `shared_inputs` and each case's `input`, then assess the returned launch options and coverage against `checks`. These fictional scenarios test policy decisions; actual host launches are needed to verify model-option support.

### Directory links for other agents

Link the whole skill directory into the skill folder of every agent that should see it. Directory links keep the instructions and configuration together and share one editable config:

```sh
ln -s "$PWD/skills/orca-poteto" ~/.agents/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.codex/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.claude/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.grok/skills/orca-poteto
```

Link `commit-style` the same way, for example `ln -s "$PWD/skills/commit-style" ~/.claude/skills/commit-style`.

For `code-turtle`, link its whole directory, for example `ln -s "$PWD/skills/code-turtle" ~/.agents/skills/code-turtle`. Keep the repository layout: its role definitions remain in `agents/turtle-*.md`, and the shared config and picker remain in `model-picker/`. A host using the linked skill must support independent subagents and load those definitions with read-only tools and the selected model options. The Claude Code plugin packages them automatically. A skill link alone does not register Claude Code plugin agents or namespaced commands.

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update the whole skill directory, including `SKILL.md`, scripts, and references. Both skills read `model-picker/` two levels above their resolved skill directory. Keep it beside `skills/` in a copied installation, preserving local model choices in `models.yaml`. Start a fresh coordinator conversation to use the updated instructions without previously loaded poteto instructions.

## Review a change

In a repository you want to review, run one of these commands:

```text
/ultrapowers:code-turtle 123
/ultrapowers:code-turtle feature-branch
/ultrapowers:code-turtle 6a93ac4
/ultrapowers:code-turtle main...feature-branch
/ultrapowers:code-turtle path:src/parser.py
```

With no target, the skill reviews tracked staged and unstaged changes against `HEAD`. A path restricts those changes. Untracked files are excluded. Use `#N` for a PR, or `path:`, `branch:`, or `commit:`, when a name is ambiguous. Branch review uses the merge base with `origin/HEAD`, `main`, or `master`; use an explicit range for another base. Commit review compares the commit with its first parent. PR review uses the merge base of the PR's base and head objects. The skill never fetches or checks out a ref.

The review saves its diff and source snapshots outside the repository and passes file pointers to each agent. Before dispatch, turtle suggests review lenses from what the diff touches and asks about them in the same question as models: `correctness` (always), `security`, `data` (migrations, schema, queries, transactions), `performance` (loops, queries, hot paths, unbounded reads), and the advisory `design` lens (boundaries, interfaces, duplication, complexity). Each suggestion shows the diff signal behind it and the resulting agent count. Name lenses in your request, or say to use defaults, to skip the question. See [review lenses](skills/code-turtle/references/lenses.md). Below 50 changed lines, one combined finder covers every selected verified lens; larger diffs run a summarizer and one finder per selected lens in parallel. Every finder role runs once per `review` model, so adding a second `review` entry in `models.yaml` doubles the finders and gives each issue a second, independent chance to be caught. Findings with the same root cause merge before verification, and each verifier runs on a model that did not find the claim when one is available. Binary changes and unavailable submodule content select the full path and appear as coverage limits.

The summary comes first. Every issue has `file`, `line`, `severity`, `lens`, `claim`, `failure_scenario`, `comment`, `verdict`, and `found_by`, the models that reported it. Issues more models agree on rank higher within the same severity and verdict.

Design notes follow the issues in their own section, labeled as opinions. They come from the `design` lens, or from a data or performance claim that holds but breaks no stated requirement. A second model judges each note as agree, partly, or disagree; disagreed notes are dropped and at most five are shown. Notes use `suggestion (non-blocking):` comments. Scenarios include a concrete input or state, the wrong result, and a quoted source line. Confirmed issues have independent static evidence; agents have read-only file tools and do not execute reproductions. Plausible issues state what remains unverified. Rejected claims are dropped. A finalization script validates the issue schema, ranks the results, caps them at ten, and saves `findings.json` and `review.md`. The orchestrator merges findings about the same root cause before that check. A clean review can contain zero issues.

Comments use Conventional Comments prefixes: `issue (blocking):`, `suggestion:`, or `question:`. Paste them into your review yourself. Version 1 never posts comments to GitHub. If an agent or verifier is unavailable, the review states the limitation and remains incomplete.

Inspired by CodeRabbit and the tortoise-and-hare story.
