# ultrapowers

Agent skills for multi-agent work coordinated by Orca. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format, so any agent that Orca launches can load it.

## Skills

- `orca-poteto`. Orca coordinates the workers. poteto-mode sets the engineering standard inside each worker. Each worker gets explicit commit, push, and PR permissions. The skill never grants merge. Status: a recommended adaptation, not a tested integration.

## Requirements

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill.

The wrapper refers to both skills by name and loads their installed copies, so updates to either skill apply without changes here.

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

Use these commands only for destinations that do not already exist. If an agent has a copied installation, update its `SKILL.md` and include the sibling `models.yaml`, or link that config to the shared file. An existing conversation must reload the skill before using the updated instructions.
