# ultrapowers

Agent skills for multi-agent work coordinated by Orca. Each skill is a folder under `skills/` in the [Agent Skills](https://agentskills.io) format, so any agent that Orca launches can load it.

## Skills

- `orca-poteto`. Orca coordinates the workers. poteto-mode sets the engineering standard inside each worker. Each worker gets explicit commit, push, and PR permissions. The skill never grants merge. Status: a recommended adaptation, not a tested integration.

## Requirements

- Orca, with its `orchestration` skill installed.
- poteto-mode (pstack), installed as a skill.

The wrapper refers to both skills by name and loads their installed copies, so updates to either skill apply without changes here.

## Install

Link each skill into the skill folder of every agent that should see it:

```sh
ln -s "$PWD/skills/orca-poteto" ~/.agents/skills/orca-poteto
ln -s "$PWD/skills/orca-poteto" ~/.claude/skills/orca-poteto
```
