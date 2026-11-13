# ultrapowers

Agent skills for multi-agent work coordinated by Orca. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format, so any agent that Orca launches can load it.

## Skills

- `orca-poteto`. An Orca coordinator assigns bounded tasks to separate poteto worker sessions. Each worker selects its poteto playbook and owns implementation, verification, and prescribed reviews. Each worker gets explicit commit, push, and PR permissions. The skill never grants merge. When a run settles with nothing waiting on the user, the coordinator removes the worktrees it created, keeps the deliverable branches, and switches its checkout back to the original branch. Status: a recommended adaptation, not a tested integration.
- `commit-style`. Atomic commits with [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) messages. The agent reads the repository's own convention first, splits the change into atomic commits, stages by path, verifies, and writes a typed header with a body that explains why. It needs neither Orca nor poteto.

## Requirements

For `orca-poteto`:

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill.

The coordinator loads the installed orchestration skill. Each worker loads the installed poteto-mode skill through an absolute path in its brief. The coordinator reads acceptance evidence and checks integration between deliverables without repeating the worker's engineering phases. Additional engineering review needs a worker request, a user request, or a concrete integration risk.

The wrapper leaves both underlying skills and their standalone settings unchanged. Updates to their installed copies apply on the next run.

## Configure agents and models

Edit [`skills/orca-poteto/models.yaml`](skills/orca-poteto/models.yaml). Each role has an `agent`, `model`, and `effort`. Use short model names or full provider IDs. Set `model` or `effort` to YAML `null` to inherit the selected agent's configured default.

The skill resolves short names against that agent's available models on the execution host. It prefers the agent's configured provider when unambiguous and asks for a full ID when it cannot select one match. The `agent` field fixes the runtime, so a model choice cannot silently switch reviewers to another agent.

At the start of a run the coordinator splits the request into units and proposes an implementation model for each one. It reads the models the host can launch, looks them up on the leaderboard at `ranking_source`, and rates each unit's demand: a hard unit gets the top-ranked model, an ordinary unit gets the `implementation` entry, and a mechanical unit gets a cheaper choice. You approve or edit the table once before anything is dispatched. The ranking is saved at `~/.cache/orca-poteto/model-ranking.md` and fetched again when the available models change or you ask for a refresh. Set `ranking_source` to `null`, or tell the run to use the defaults, to run every unit on the `implementation` entry. Reviewer models stay the same for the whole run.

Explicit instructions for a run override individual fields without editing the file. The skill reads the config beside its own installed `SKILL.md`, not from the project being worked on.

## Install

Link the whole skill directory into the skill folder of every agent that should see it. Directory links keep the instructions and configuration together and share one editable config:

```sh
ln -s "$PWD/skills/orca-poteto" ~/.agents/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.codex/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.claude/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.grok/skills/orca-poteto
```

Link `commit-style` the same way, for example `ln -s "$PWD/skills/commit-style" ~/.claude/skills/commit-style`.

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update the whole skill directory, including `SKILL.md`, everything under `references/`, and the sibling `models.yaml`. Preserve any local model choices, or link that config to the shared file. Start a fresh coordinator conversation to use the updated instructions without previously loaded poteto instructions.
