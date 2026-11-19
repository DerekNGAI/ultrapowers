# Finding schema

Finders return a JSON array. Use `[]` when no defect meets this schema. Each candidate has exactly these seven fields.

| Field | Type | Content |
| --- | --- | --- |
| `file` | string | Repository-relative path, without an absolute prefix or `..` segments. |
| `line` | positive integer | An anchor in the changed code at the reviewed revision. Use the before snapshot for a deleted line. |
| `severity` | string | `blocking`, `should-fix`, or `minor`. |
| `lens` | string | The [lens](lenses.md) the defect belongs to: `correctness`, `security`, `data`, or `performance`. |
| `claim` | string | One sentence stating the defect introduced by this change. |
| `failure_scenario` | string | A concrete input or state, the wrong result, and an exact quote of the offending source line. |
| `comment` | string | A complete, pasteable Conventional Comment that names the problem, trigger, and requested correction. |

Use `blocking` for a demonstrated release blocker, such as data loss, an exploitable vulnerability, or failure of a core flow. Use `should-fix` for an actionable defect in any lens. Use `minor` for a limited behavioral defect. Omit style, formatting, speculative improvements, and pre-existing defects.

A wrong result must violate a requirement, an invariant, or an established caller expectation found in the sources. Identify that basis in `failure_scenario`. A documented policy doing what it says is not a defect merely because another policy could be preferable. Missing evidence of a requirement is grounds to reject the claim, not to label an optional improvement `plausible`. A `data` or `performance` claim needs the basis its lens names in [lenses](lenses.md).

Comments start with `issue (blocking):`, `suggestion:`, or `question:`. Reserve `issue (blocking):` for confirmed blocking findings. Use `suggestion:` for confirmed nonblocking defects. A plausible finding uses `question:`, states the uncertainty, and asks for the missing evidence. A plausible finding cannot have `blocking` severity.

Keep the comment within the independently supported trigger and consequence. A proven failing input does not establish that every input fails. Check universal words such as "every" and "always" against valid counterexamples before keeping them.

The verifier receives only `file`, `line`, and `claim` from the candidate, along with neutral review pointers. It returns this separate record:

```json
{
	"verdict": "confirmed",
	"evidence": "An independently checked trigger, result, and exact source quote."
}
```

| Verdict | Meaning |
| --- | --- |
| `confirmed` | The actual code and its callers establish the failure scenario. State whether this is static evidence or an executed reproduction. |
| `plausible` | The code supports the claim, but a named environmental or runtime fact remains unverified. Name that fact. |
| `rejected` | The claim is false, pre-existing, unsupported by the available code, or lacks a concrete failure scenario. |

Confirmation must support the exact claim and its consequence. Conflicting prose instructions establish an instruction conflict; they do not prove which instruction a future agent follows. Narrow a confirmed claim to the proven conflict, or label the downstream outcome `plausible` and name that uncertainty. Reject an optional improvement unless an observable failure or a violated requirement supports it.

For a rejected claim, `evidence` gives the counterexample or missing support. A missing or failed verifier is a review limitation, not a verdict.

The orchestrator reconciles each surviving candidate with the verifier's independent evidence, then adds `verdict` and `found_by`. `found_by` is a nonempty list of the distinct resolved model IDs whose finders reported that root cause, taken from `model-dispatches.json`, never from a finder's own statement. Label an inherited model `inherited:<agent>`. Every reported issue has exactly the seven candidate fields plus `verdict` and `found_by`. When finders in different lenses report one root cause, keep the lens that best names it. Keep verifier evidence in the saved review artifacts. Drop rejected claims. Merge duplicate root causes and the union of their `found_by` lists, sort by severity, verdict, and then the number of agreeing models, and report at most ten issues.
