Run the shared dual-review workflow on this project's current change.
The judge must snapshot it, launch ultrapowers-reviewer-a and
ultrapowers-reviewer-b concurrently, judge every finding with evidence, delegate
accepted fixes and checks to built-in general, and return rejected substantive
finding IDs to their originating reviewer.
The judge must not edit files. Wait for both reviewers before delegating fixes,
and wait for general before capturing the revised snapshot.
Use at most three review rounds with one rebuttal exchange per reviewer per round.
Finish with the overall outcome, verification results, and the final verdict
and finding tables required by the shared protocol.

Additional user scope or review focus: $ARGUMENTS
