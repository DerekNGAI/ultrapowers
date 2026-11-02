# Poteto worker contract

Apply this contract only to the `orca-poteto` task in your brief. Load the installed `poteto-mode/SKILL.md` from the brief's `SKILLS` path in this worker session. Keep the installed skills and shared settings unchanged.

## Engineering ownership

Select the per-unit poteto playbook or review skill for your assigned role, then load its routed skills as needed. Own the task's design, implementation, verification, prescribed reviews, commits, and PR description within the brief's scope and permissions. Review workers return findings. Implementation workers make fixes.

Include review findings and their resolution in the completion evidence so the coordinator can check acceptance without repeating your workflow.

## Coordination

Orca's coordinator owns task dependencies and long-lived worker sessions through orchestration. Use poteto's per-unit playbooks, such as Feature, Bug fix, and Refactoring. Route project-level work to the coordinator. Do not run poteto's Orchestrate, Autopilot-full, or Autopilot-stack playbooks, or its `scripts/orch` store.

You may use poteto's short-lived engineering helpers that finish inside your turn, such as `interrogate`, `architect`, or `swarm` verification. A local helper must honor the resolved agent, model, and effort in `MODEL_POLICY`. A model override alone does not change its runtime. If the local helper tool cannot honor that policy, ask the coordinator to dispatch the helper through Orca. You retain ownership of the engineering workflow. Start no Orca workers yourself.

Ask questions with the `ask` command from your Orca preamble. Poteto's question rules decide whether a question is worth asking. Use that coordinator channel instead of a local question tool.

## Models

Use the brief's resolved `MODEL_POLICY` for your role and every helper. It includes both implementation and review roles and overrides pstack's model choices and automatic effort adjustments for this run. Preserve each routed skill's reviewer count unless the user overrides it.

Use the resolved choices instead of loading another copy of `models.yaml` or resolving model names again. If a selection becomes unavailable or unverifiable, stop that unit and report the problem through the coordinator. Never silently substitute an agent, model, or effort.

## Permissions

- A missing or unclear `PERMISSIONS` line means no.
- A grant covers only the named branch or base, and only the files in the brief's Ownership.
- The coordinator grants only what the user granted to it. It cannot grant merge.
- The brief's permissions override poteto's Autonomy section for git and forge actions. Poteto's Always-pause list still applies.
- Never, under any grant: merge, enable auto-merge, force-push, retarget an existing PR, or rebase a branch that another agent uses.
- With `commit: yes`, poteto's commit rules apply. With `pr: yes`, poteto's Opening a PR playbook applies. Post the PR URL and finish the task without babysitting or shipping.
- If the work needs a permission the brief does not grant, stop at the last allowed step and `ask` the coordinator. The coordinator asks the user.

## Completion

Report completion once with `worker_done`. Write poteto's full reply to a file and pass it as `--report-path`.

Include the branch, head SHA, PR URL if any, verification commands and results, verdict, deviations, review evidence, and remaining blockers. Report the requested and effective agent, model, and effort, including inherited fields or unavailable status.
