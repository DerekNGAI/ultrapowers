# ultrapowers

Agent skills for multi-agent work coordinated by Orca. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format, so any agent that Orca launches can load it.

## Skills

- `orca-poteto`. An Orca coordinator assigns bounded tasks to separate poteto worker sessions. Each worker selects its poteto playbook and owns implementation, verification, and prescribed reviews. Each worker gets explicit commit, push, and PR permissions. The skill never grants merge. Status: a recommended adaptation, not a tested integration.

## Requirements

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill.

The coordinator loads the installed orchestration skill. Each worker loads the installed poteto-mode skill through an absolute path in its brief. The coordinator reads acceptance evidence and checks integration between deliverables without repeating the worker's engineering phases. Additional engineering review needs a worker request, a user request, or a concrete integration risk.

The wrapper leaves both underlying skills and their standalone settings unchanged. Updates to their installed copies apply on the next run.

## Configure agents and models

Edit [`skills/orca-poteto/models.yaml`](skills/orca-poteto/models.yaml). Each role has an `agent`, `model`, and `effort`. Use short model names or full provider IDs. Set `model` or `effort` to YAML `null` to inherit the selected agent's configured default.

The skill resolves short names against that agent's available models on the execution host. It prefers the agent's configured provider when unambiguous and asks for a full ID when it cannot select one match. The `agent` field fixes the runtime, so a model choice cannot silently switch reviewers to another agent.

Explicit instructions for a run override individual fields without editing the file. The skill reads the config beside its own installed `SKILL.md`, not from the project being worked on.

## Install

Link the whole skill directory into the skill folder of every agent that should see it. Directory links keep the instructions and configuration together and share one editable config:

```sh
ln -s "$PWD/skills/orca-poteto" ~/.agents/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.codex/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.claude/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.grok/skills/orca-poteto
```

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update the whole skill directory, including `SKILL.md`, `references/worker-contract.md`, and the sibling `models.yaml`. Preserve any local model choices, or link that config to the shared file. Start a fresh coordinator conversation to use the updated instructions without previously loaded poteto instructions.
