# ultrapowers

Agent skills for multi-agent work coordinated by Orca, model selection, and atomic commits. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format. The repository root is also a Claude Code plugin named `ultrapowers`.

## Skills

- `orca-poteto`. The default flow for every implementation task. The coordinator splits the request into units and tiers each one: it does `trivial` units itself in its own worktree, gives `standard` units to plain Orca workers, and gives `complex` units (several repositories or many files, open design, migrations, schema, or security) to Orca workers running poteto-mode. It posts each unit's tier and reason before dispatch, and starts independent units in parallel. Every unit ships as a pull request: commit, push its own branch, open the PR. Say "no PR" or "local only" to stop at the commit. The skill never merges. When a run settles with nothing waiting on the user, the coordinator cleans up without asking: it releases its workers, closes the terminals it opened, removes its worktrees and their pushed local branches (remote branches and PRs stay), deletes its scratch files, and switches your checkout back to the original branch. Status: a recommended adaptation, not a tested integration.
- `model-picker`. Picks the agent, model, and effort for each role before a skill dispatches agents, with a Best value / Lowest cost / Highest capability proposal and one question. Other skills and agents, such as Codex, load it as a regular skill. See [Configure agents and models](#configure-agents-and-models).
- `commit-style`. Atomic commits with [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) messages. The agent reads the repository's own convention first, splits the change into atomic commits, stages by path, verifies, and writes a typed header with a body that explains why. It needs neither Orca nor poteto.

## Requirements

For `orca-poteto`:

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill, for complex units.
- The `model-picker` skill from this repository.
- A push remote and an authenticated GitHub CLI (`gh`), to open each unit's PR.

The coordinator loads the installed orchestration skill. Each complex worker loads the installed poteto-mode skill through an absolute path in its brief. Before dispatching any worker, the coordinator stops and asks the model question; say "use the defaults" in your request to skip it. Runs with only trivial units ask nothing. The coordinator reads acceptance evidence and checks integration between deliverables without repeating the worker's engineering phases. Additional engineering review needs a worker request, a user request, or a concrete integration risk.

The wrapper leaves both underlying skills and their standalone settings unchanged. Updates to their installed copies apply on the next run.

## Configure agents and models

`orca-poteto` uses the [`model-picker`](skills/model-picker/SKILL.md) skill, and any other skill or agent can load it the same way. Edit [`skills/model-picker/models.yaml`](skills/model-picker/models.yaml). Each role has an `agent`, `model`, and `effort`. Use short model names or full provider IDs. Set `model` or `effort` to YAML `null` to inherit the selected agent's configured default.

The picker resolves short names against that agent's available models on the execution host. It prefers the agent's configured provider when unambiguous and asks for a full ID when it cannot select one match. The `agent` field fixes the runtime, so a model choice cannot silently switch reviewers to another agent.

Before dispatch, the picker asks one question. It offers up to three distinct model choices per unit: **Best value** (recommended), **Lowest cost** that meets the task's needs, and **Highest capability**. The table compares task-relevant capability evidence, supported effort, and input/output token prices with units, sources, and dates. Hard work does not automatically select the most expensive model or maximum effort. Duplicate choices share one row; unavailable evidence stays unknown. You choose or edit one row per unit before dispatch. Review models are a multi-select: `models.yaml`'s `review` entries start selected, and you can add suggested or other available models for this run without editing the file. Explicit model choices and requests to use defaults bypass the suggestions they settle. Reviewer models stay the same for the whole run. Each calling skill adds its own role map and can add its own items to the question.

Capability and pricing evidence is saved at `~/.cache/ultrapowers/model-ranking.md` and refreshed when the source or candidate coverage changes, the UTC date changes, or you ask. Price comparisons use the selected provider's published billing terms; public API prices may differ from your actual charges. A stated input/output mix supports comparisons when rates cross. When capability data is unavailable or `ranking_source` is `null`, the picker offers the configured default. When prices are unavailable, it shows capability alternatives without claiming a value or cost winner.

Explicit instructions for a run override individual fields without editing the file. The picker reads the `models.yaml` inside its own installed skill folder, not from the project being worked on.

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

The plugin exposes `/ultrapowers:orca-poteto`, `/ultrapowers:model-picker`, and `/ultrapowers:commit-style`. It adds no agents, hooks, or global model settings.

Validate a local copy with `claude plugin validate /absolute/path/to/ultrapowers`. See the official [plugin component reference](https://code.claude.com/docs/en/plugins/components) for supported metadata.

Model-picker changes can be replayed against the fictional [behavioral scenarios](skills/model-picker/tests/model-proposal-cases.json); give an evaluator only the inputs, then assess its choices against the checks.

### Directory links for other agents

Link the whole skill directory into the skill folder of every agent that should see it. Directory links keep the instructions and configuration together and share one editable config:

```sh
ln -s "$PWD/skills/orca-poteto" ~/.agents/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.codex/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.claude/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.grok/skills/orca-poteto
```

Link `model-picker` and `commit-style` the same way, for example `ln -s "$PWD/skills/model-picker" ~/.codex/skills/model-picker`. `orca-poteto` needs `model-picker` installed beside it.

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update the whole skill directory, including `SKILL.md` and references. For `model-picker`, preserve local model choices in `models.yaml`. Start a fresh coordinator conversation to use the updated instructions without previously loaded poteto instructions.
