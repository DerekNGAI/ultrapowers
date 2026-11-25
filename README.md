# ultrapowers

Agent skills for multi-agent work coordinated by Orca, model selection, and atomic commits. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format. The repository root is also a Claude Code plugin named `ultrapowers`.

## Skills

- `ultrapowers-orca-poteto`. The default flow for every implementation task: setup, size and pick models, dispatch, finish, clean up. The coordinator never edits code. Each unit goes to one Orca worker: a plain worker for `simple` units (one or two files, obvious change), a poteto-mode worker with multi-model reviewers for `complex` ones. Units run one at a time unless you or your plan ask for parallel work. Every unit ships as a pull request; say "no PR" or "local only" to stop at the commit. Nothing is merged. When the run settles, the coordinator releases its workers, removes its clean worktrees and pushed local branches (remote branches and PRs stay), deletes its scratch files, and switches your checkout back.
- `ultrapowers-model-picker`. Suggests the models for implementation and review every run (Best value / Lowest cost / Highest capability) plus an effort budget, then waits for your pick. For poteto workers it writes poteto's role lines, like `/setup-pstack` does, into the worker brief. There is no default model file. See [Models](#models).
- `ultrapowers-commit-style`. Atomic commits with [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) messages. The agent reads the repository's own convention first, splits the change into atomic commits, stages by path, verifies, and writes a typed header with a body that explains why. It needs neither Orca nor poteto.

## Requirements

For `ultrapowers-orca-poteto`:

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill, for complex units.
- The `ultrapowers-model-picker` skill from this repository.
- A push remote and an authenticated GitHub CLI (`gh`), to open each unit's PR.

The coordinator loads the installed orchestration skill. Each complex worker reads poteto-mode through an absolute path in its brief, with ultrapowers-model-picker's poteto role lines in place of `~/.cursor/rules/pstack-models.mdc`. Poteto then runs its own flow, including when to review, unchanged. Before dispatching, the coordinator asks the model question and waits for your reply. If a worker gets stuck at a prompt such as Codex's hooks review, the coordinator asks you to answer it rather than disabling hooks.

The wrapper leaves both underlying skills and their standalone settings unchanged. Updates to their installed copies apply on the next run.

## Models

`ultrapowers-orca-poteto` uses the [`ultrapowers-model-picker`](skills/ultrapowers-model-picker/SKILL.md) skill, and any other skill or agent can load it the same way. Every run, it lists the models each installed agent can launch, keeping each model on its own vendor's agent (GPT on Codex, Claude on Claude Code, Grok on Grok Build), ranks them against [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models) and provider pricing, and asks one question:

- **Implementation**, per unit: up to three rows, **Best value** (recommended), **Lowest cost**, and **Highest capability**, with capability evidence, effort, and input/output prices.
- **Review models**, when a unit is complex: a multi-select with two models from different providers recommended.
- **Budget**: `large` (xhigh), `medium` (high), or `small` (medium), the effort every role runs at, as in `/setup-pstack`.

For each complex unit, the picks become poteto's role lines: the implementation model fills the code, judgment, and swarm roles, and the review models fill `interrogate reviewers`, `arena runners`, and `arena cross-judge pool`. Poteto runs one reviewer per listed model, so the number of review models you pick sets the review cost. A reviewer on another agent than the worker's, such as Claude for a Codex worker, runs as an Orca helper worker on that agent. The machine-wide pstack rule file is never written.

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

The plugin exposes `/ultrapowers:ultrapowers-orca-poteto`, `/ultrapowers:ultrapowers-model-picker`, and `/ultrapowers:ultrapowers-commit-style`. It adds no agents, hooks, or global model settings.

Validate a local copy with `claude plugin validate /absolute/path/to/ultrapowers`. See the official [plugin component reference](https://code.claude.com/docs/en/plugins/components) for supported metadata.

Model-picker changes can be replayed against the fictional [behavioral scenarios](skills/ultrapowers-model-picker/tests/model-proposal-cases.json); give an evaluator only the inputs, then assess its choices against the checks.

### Directory links for other agents

Link the whole skill directory into the skill folder of every agent that should see it. Directory links keep the instructions and configuration together and share one editable config:

```sh
ln -s "$PWD/skills/ultrapowers-orca-poteto" ~/.agents/skills/ultrapowers-orca-poteto
ln -s "$PWD/skills/ultrapowers-orca-poteto" ~/.codex/skills/ultrapowers-orca-poteto
ln -s "$PWD/skills/ultrapowers-orca-poteto" ~/.claude/skills/ultrapowers-orca-poteto
ln -s "$PWD/skills/ultrapowers-orca-poteto" ~/.grok/skills/ultrapowers-orca-poteto
```

Link `ultrapowers-model-picker` and `ultrapowers-commit-style` the same way, for example `ln -s "$PWD/skills/ultrapowers-model-picker" ~/.codex/skills/ultrapowers-model-picker`. `ultrapowers-orca-poteto` needs `ultrapowers-model-picker` installed beside it.

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update the whole skill directory, including `SKILL.md` and references. Start a fresh coordinator conversation to use the updated instructions without previously loaded poteto instructions.
