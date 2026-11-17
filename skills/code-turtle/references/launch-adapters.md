# Review launch adapters

Load the shared selector's [host contract](../../model-selector/references/host-contract.md). The approved policy fixes each role's runtime, model, effort, inherited fields, and adapter. Use one independent task per role or claim. The model choice belongs in launch options or a session definition, never in the review prompt.

## Claude Agent

Use declared `ultrapowers:turtle-summarizer`, `ultrapowers:turtle-bug-hunter`, `ultrapowers:turtle-security`, and `ultrapowers:turtle-verifier` types. Keep their `Read, Grep, Glob` tools. The installed plugin registers these types. A directory link alone does not register them.

In the host inventory, offer `claude-agent` for verified aliases and inheritance. Check the current Agent tool schema for effort support. Aliases are `haiku`, `sonnet`, `opus`, or `fable`. For an explicit alias, pass the policy's `launch.model` as the Agent `model` option. For inherited model, omit that option and use the role definition's `inherit`. Pass an explicit effort only when the schema and model support it. Never pass full IDs in `Agent.model`.

Keep the summarizer's Haiku default through its approved alias. Explicit alias overrides can choose another family. Offer this adapter only when effective child metadata or request traces are accessible to the caller. Otherwise use a verified CLI route that pins the parent settings and preserves their inherited markers. An inherited parent model is not an explicit override.

For request evidence, start the parent session with `OTEL_LOG_RAW_API_BODIES=file:/outside/checkout/fresh-trace-directory`. Use a separate trace directory for each review. After each completed role, audit its actual requests and responses:

```sh
python3 /resolved/skills/code-turtle/scripts/claude_review.py audit bug-hunter \
  --policy /artifact/model-selection.json --context /artifact/context.json \
  --trace /outside/checkout/fresh-trace-directory
```

The audit checks the declared role's request source, exact model, effort, read-only tools, and response model. It writes a separate `selection.json` outside the checkout. Audit every dispatched type, including verifier when used. An audit covers every instance of that type in this review's trace. Save native call options and confirm each child completed independently. Missing traces, failed child calls, or an audit mismatch make the review incomplete. Do not accept those findings or claim completion. The final output starts with `review.md`'s summary and places model evidence in the coverage note.

## Claude CLI

Use this route when an exact full ID is selected or the native Agent tool cannot apply the selected effort. Verify installed `claude --help` has `--agents`, `--agent`, `--model`, `--effort`, `--tools`, and `--allowedTools`. Verify raw request logging support through `OTEL_LOG_RAW_API_BODIES=file:<directory>` and a live probe before offering this adapter. Tested on Claude Code 2.1.326.

Run the caller's adapter script, resolving its path through the real skill directory:

```sh
python3 /resolved/skills/code-turtle/scripts/claude_review.py run bug-hunter \
  --policy /artifact/model-selection.json --context /artifact/context.json
```

Roles are `summarizer`, `bug-hunter`, `security`, and `verifier`. For a verifier, create a separate JSON file with exactly `file`, `line`, and `claim` and pass `--claim /artifact/one-claim.json`. The adapter rejects extra candidate fields. It supplies only those three fields and neutral pointers. It never passes the policy, summary, finder output, or previous session to the child.

The adapter loads the original role body into a session-only `--agents` definition and selects it with `--agent`. It pins the approved exact ID with `--model` and applies `--effort` when resolved. CLI inheritance pins verified parent settings while retaining inherited markers in `selection.json`. Each role is a fresh process with no resume, a separate artifact directory, only `Read, Grep, Glob`, no MCP servers, and no slash commands. The role cannot invoke code-turtle recursively or dispatch children. The adapter leaves installed files and settings unchanged.

The output directory contains `result.txt`, the clean `input.json`, runtime events, request traces, and `selection.json`. The script validates the result model, indexed request/response models for the child session, request effort, and tool set before accepting output. A mismatch, denied read, absent trace, timeout, or failed process leaves `complete: false` and exits with an error. Omit its findings and report the limitation. Raw requests contain review content and remain in the private artifact directory outside the checkout. Inspect `selection.json` for requested/effective choices; keep raw requests with the review evidence.

`CLAUDE_CODE_EFFORT_LEVEL` and managed settings can override effort. Discovery must account for them. The adapter detects effective mismatches and never retries with another setting. Requested flags alone are insufficient.

## Other native hosts

A linked skill can use that host's independent subagent mechanism and the same role files. Offer `native` only for model and effort options the actual tool schema supports on the current runtime. Preserve `Read, Grep, Glob` or an equivalent enforced read-only set. Keep verifier input clean. Save effective child metadata, not a model name in the prompt. A native model option does not switch runtimes. If the host cannot enforce the selected settings or read-only tools, report the review incomplete.

Orca workers use the same selector through orca-poteto's separate `orca` adapter. Code-turtle does not turn review roles into poteto engineering workers or import their full briefs.
