# ultrapowers

Agent skills for multi-agent work coordinated by Orca, model selection, and atomic commits. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format. The repository root is also a Claude Code plugin named `ultrapowers`.

## Skills

- `orca-poteto`. The default flow for every implementation task: setup, size and pick models, dispatch, finish, clean up. The coordinator never edits code. Each unit goes to one Orca worker: a plain worker for `simple` units (one or two files, obvious change), a poteto-mode worker for `complex` ones, which must run independent reviewers on your picked review models, capped by the review budget, before its PR. Units run one at a time unless you or your plan ask for parallel work. Every unit ships as a pull request; say "no PR" or "local only" to stop at the commit. Nothing is merged. When the run settles, the coordinator releases its workers, removes its clean worktrees and pushed local branches (remote branches and PRs stay), deletes its scratch files, and switches your checkout back.
- `model-picker`. Suggests the agent, model, and effort for implementation and review every run (Best value / Lowest cost / Highest capability), then waits for your pick. There is no default model file. See [Models](#models).
- `commit-style`. Atomic commits with [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) messages. The agent reads the repository's own convention first, splits the change into atomic commits, stages by path, verifies, and writes a typed header with a body that explains why. It needs neither Orca nor poteto.

## Requirements

For `orca-poteto`:

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill, for complex units.
- The `model-picker` skill from this repository.
- A push remote and an authenticated GitHub CLI (`gh`), to open each unit's PR.

The coordinator loads the installed orchestration skill. Each complex worker reads poteto-mode through an absolute path in its brief, and your review models replace poteto's own reviewer models. Before dispatching, the coordinator asks the model question and waits for your reply. If a worker gets stuck at a prompt such as Codex's hooks review, the coordinator asks you to answer it rather than disabling hooks.

The wrapper leaves both underlying skills and their standalone settings unchanged. Updates to their installed copies apply on the next run.

## Models

`orca-poteto` uses the [`model-picker`](skills/model-picker/SKILL.md) skill, and any other skill or agent can load it the same way. Every run, it lists the models each installed agent can launch, ranks them against [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models) and provider pricing, and asks one question:

- **Implementation**, per unit: up to three rows, **Best value** (recommended), **Lowest cost**, and **Highest capability**, with capability evidence, effort, and input/output prices.
- **Review models**, when a unit is complex: a multi-select with two models from different providers recommended.
- **Review budget**: reviewer helpers per complex unit, default 2.

Reply with your picks, or `recommended`. Naming models in your request skips the items it settles. Short model names must match exactly; ambiguous names get a follow-up question. Evidence is cached at `~/.cache/ultrapowers/model-ranking.md` for the day; when no ranking is available, the picker lists the launchable models unranked and asks you to choose.

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

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update the whole skill directory, including `SKILL.md` and references. Start a fresh coordinator conversation to use the updated instructions without previously loaded poteto instructions.
