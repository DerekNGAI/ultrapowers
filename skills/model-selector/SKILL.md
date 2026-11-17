---
name: model-selector
description: Select verified runtime, model, and effort choices for orca-poteto or code-turtle before agents launch.
---

# Model selector

Own selection policy here. Callers own launch, isolation, role prompts, artifacts, and cleanup. A provider is not a runtime.

## Select before dispatch

1. Resolve this directory through symlinks. Read [models.json](models.json), the only defaults for both callers. Use the caller's profile. Missing files or invalid config stop dispatch. Python 3.12 or newer is required.
2. Discover capabilities on the execution host using [the host contract](references/host-contract.md). Include only launch routes that preserve the caller's role restrictions. A configured model is a candidate only after its runtime, exact ID, effort, and launch route are verified. Resolve choices with `scripts/select_models.py`. Keep unavailable runtimes unavailable.
3. Build proposals using [model proposal](references/model-proposal.md). Apply explicit user choices field by field over the profile. An implementation model named for several units applies to each covered unit. A review list replaces that list. Leave the file unchanged unless the user asks to save choices. `null` inherits the selected runtime's defaults. It never means pstack defaults. `use defaults` skips ranking and the question, while preserving any explicit overrides.
4. Ask once for unsettled choices before dispatch. For Orca, show implementation proposals per unit, the shared review entries, and the review budget. For code-turtle, show summarizer, finder, and verifier choices. The finder choice applies to both correctness and security finders. This is configuration only. Show no candidate findings. Skip fields the request already settles. Wait for approval unless the user settled every field or requested defaults.
5. Save the approved resolved policy outside the checkout. It contains `requested`, `resolved`, `inherited`, adapter, launch arguments, evidence, and initially null `effective` for each role. Resolve each distinct choice once per run. Carry the approved policy into workers instead of reloading another installed config. At launch, record actual effective runtime, model, and effort evidence. Compare it with the approved policy before accepting results. A prompt containing a model name or requested flags alone proves nothing.

## Resolution and output

The resolver validates complete config and partial role overrides. Run it from any working directory:

```sh
python3 /resolved/skills/model-selector/scripts/select_models.py code-turtle \
  --host /outside/checkout/host.json --overrides /outside/checkout/overrides.json
```

Omit `--overrides` when using the profile. Save stdout as the approved policy after approval. For a per-unit proposal, resolve that unit's implementation override with the same shared review entries and budget.

`review_budget` caps Orca engineering reviewers. Keep it `null` for code-turtle, whose size gate and per-claim verification determine dispatch counts.

Full IDs require an exact catalog match. Short names compare complete model names or verified aliases, with no substring, prefix, version, or variant substitution. Multiple matches prefer the selected runtime's configured provider only when discovery identifies it unambiguously. Bare IDs get no priority. Remaining ambiguity requires a full ID.

Validate effort for the selected model. An explicit effort with an inherited model resolves the runtime default model first. Preserve the inherited marker even when the adapter needs its exact ID as a launch argument. Unsupported or unverifiable choices stop that role or unit. Report the path, requested choice, and missing evidence. Never silently change runtime, model, or effort, including after a catalog change.

Return a compact configuration table containing role or unit, runtime, requested model, resolved ID, effort, and inherited fields. Keep ranking source/date, unranked candidates, review budget, and resolution evidence with the saved policy. After launch, report requested and effective choices and any incomplete verification. Code-turtle keeps this configuration step before review, then preserves its summary-first review output.
