# Review model policy

Resolve models after preparing a nonempty diff and before dispatching any review agent. Read the shared [model picker](../../../model-picker/PICKER.md), resolving its path after following directory symlinks. It owns the config file, precedence, the single question, name resolution, dispatch options, and the audit rules. Model selection is orchestration metadata; keep it separate from the reviewed source and candidate evidence.

## Caller contract

Supply the picker this role map:

| Role | Entry |
| --- | --- |
| Summarizer, in full mode | `implementation`, as a non-review helper |
| Bug hunter and security finder | `review` entries in order, cycling if needed |
| Each fresh verifier | `review`, preferring an entry different from its finder when available |

- **Proposal units.** The review roles, each defaulting to its mapped entry. Keep an explicitly supplied review list fixed. Show the summarizer and review selections in the same question.
- **Catalog sources.** The dispatch routes this host can actually launch; Orca is not required.
- **Audit location.** `model-dispatches.json` beside `context.json`. Add the candidate file and line for each verifier. Save no finder reasoning in a verifier's prompt.

The small-mode summary is written by the parent and needs no summarizer selection.

## Reviewer budget

Keep the standalone skill's full reviewer count unless the user explicitly sets `review_budget`. Inside a worker, honor the enclosing brief's remaining `REVIEW_BUDGET`; the config's per-worker budget does not cap a standalone review. Each finder and verifier consumes one reviewer slot; the summarizer does not. Apply the budget in workflow order: required finders first, then verifiers for valid candidates in severity order. Preserve the separate finder and verifier stages. If an explicit or enclosing budget cannot cover them, report incomplete coverage and omit claims without an independent verdict. A user can request `review_budget: null` to retain the full count. Do not combine a finder with its verifier to fit a budget.

## Dispatch

Load each role's definition from `../../../agents/turtle-*.md` relative to this reference, following directory symlinks. Preserve its read-only behavior. Use fresh, non-fork agents with only the role instructions and the neutral review pointers. A verifier also receives only `{file, line, claim}` from one candidate. Selecting another model never grants it the parent's transcript.

Claude Code role types are `ultrapowers:turtle-…`; Codex role types are `turtle-…`. Pass the picker's options on **every** finder, summarizer, and verifier invocation. A failed required dispatch makes the review incomplete.

Include the picker's per-role audit in the final coverage note.
