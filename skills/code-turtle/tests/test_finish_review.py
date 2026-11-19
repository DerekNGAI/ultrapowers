import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "finish_review.py"


class FinishReviewTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="turtle-finish-test-")
        self.addCleanup(self.workspace.cleanup)
        root = Path(self.workspace.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.artifacts = root / "artifacts"
        self.artifacts.mkdir()
        before = self.artifacts / "before"
        after = self.artifacts / "after"
        before.mkdir()
        after.mkdir()
        for name in ["billing.py", "z.py"] + [f"file-{index:02}.py" for index in range(12)]:
            (after / name).write_text("def total_cents(price, count):\n    return price + count\n    return price + count\n")
        (self.artifacts / "context.json").write_text(json.dumps({"repo_root": str(self.repo), "before_root": str(before), "after_root": str(after)}))
        (self.artifacts / "summary.md").write_text("The change replaces multiplication with addition. It changes the order total.\n")

    def finding(self, **overrides):
        return dict(file="billing.py", line=2, severity="should-fix", lens="correctness", claim="The total adds instead of multiplying.",
                    failure_scenario="total_cents(500, 3) returns 503 instead of 1500 at `return price + count`.",
                    comment="suggestion: Restore multiplication so three items at 500 cents total 1500.",
                    verdict="confirmed", found_by=["model-a"]) | overrides

    def note(self, **overrides):
        return dict(file="billing.py", line=2, lens="design",
                    note="Pricing math sits in the formatter module, unlike the rest of billing.",
                    comment="suggestion (non-blocking): Move total_cents beside the other pricing helpers.",
                    second_opinion="agree", found_by=["model-a"]) | overrides

    def finish(self, findings, notes=None):
        (self.artifacts / "reviewed-findings.json").write_text(json.dumps(findings))
        if notes is not None:
            (self.artifacts / "reviewed-notes.json").write_text(json.dumps(notes))
        return subprocess.run([sys.executable, str(SCRIPT), str(self.artifacts)], capture_output=True, text=True)

    def test_missing_verdict_cannot_produce_final_artifacts(self):
        finding = self.finding()
        del finding["verdict"]
        result = self.finish([finding])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verdict", result.stderr)
        self.assertFalse((self.artifacts / "findings.json").exists())
        self.assertFalse((self.artifacts / "review.md").exists())

    def test_invalid_schema_and_certainty_are_rejected(self):
        for overrides in ({"extra": "field"}, {"line": True}, {"file": "../billing.py"},
                          {"verdict": "rejected"}, {"verdict": "plausible"},
                          {"verdict": "plausible", "severity": "blocking", "comment": "question: Is this reachable?"},
                          {"found_by": []}, {"lens": "style"}, {"found_by": "model-a"}, {"found_by": ["model-a", "model-a"]}, {"found_by": [""]}):
            with self.subTest(overrides=overrides):
                self.assertNotEqual(self.finish([self.finding(**overrides)]).returncode, 0)

    def test_output_is_deduplicated_ranked_capped_and_summary_first(self):
        findings = [self.finding(file=f"file-{index:02}.py", severity="minor") for index in range(12)]
        findings += [self.finding(file="z.py", claim="An unverified runtime fails.", verdict="plausible", comment="question: Does the runtime allow this input?"), self.finding()]
        findings += [self.finding(line=3)]
        result = self.finish(list(reversed(findings)))
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads((self.artifacts / "findings.json").read_text())
        self.assertEqual(len(saved), 10)
        self.assertEqual([item["file"] for item in saved[:2]], ["billing.py", "z.py"])
        self.assertEqual(saved[0]["line"], 2)
        self.assertTrue(all(len(item) == 9 for item in saved))
        self.assertTrue(result.stdout.startswith("## Summary\n"))
        self.assertIn("4 additional issues omitted", result.stdout)
        self.assertEqual((self.artifacts / "review.md").read_text(), result.stdout)
        self.assertIn("**verdict:** plausible", result.stdout)

    def test_duplicates_merge_their_models_and_agreement_ranks_first(self):
        findings = [self.finding(), self.finding(found_by=["model-b"]), self.finding(found_by=["model-a", "model-b"]),
                    self.finding(file="z.py", claim="A second defect.", found_by=["model-a", "model-b", "model-c"])]
        result = self.finish(findings)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads((self.artifacts / "findings.json").read_text())
        self.assertEqual([(item["file"], item["found_by"]) for item in saved],
                         [("z.py", ["model-a", "model-b", "model-c"]), ("billing.py", ["model-a", "model-b"])])
        self.assertIn("**found_by:** model-a, model-b", result.stdout)
        self.assertIn("**lens:** correctness", result.stdout)

    def test_design_notes_follow_issues_ranked_and_capped(self):
        notes = [self.note(file=f"file-{index:02}.py", second_opinion="partly") for index in range(6)]
        notes += [self.note(), self.note(found_by=["model-b"])]
        result = self.finish([self.finding()], notes)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads((self.artifacts / "notes.json").read_text())
        self.assertEqual(len(saved), 5)
        self.assertEqual((saved[0]["file"], saved[0]["found_by"]), ("billing.py", ["model-a", "model-b"]))
        self.assertLess(result.stdout.index("## Issues"), result.stdout.index("## Design notes"))
        self.assertIn("Opinions, not verified defects.", result.stdout)
        self.assertIn("2 additional design notes omitted", result.stdout)

    def test_design_section_appears_only_when_the_lens_ran(self):
        self.assertNotIn("## Design notes", self.finish([]).stdout)
        self.assertFalse((self.artifacts / "notes.json").exists())
        self.assertIn("No design notes.", self.finish([], []).stdout)

    def test_invalid_design_notes_are_rejected(self):
        for overrides in ({"second_opinion": "disagree"}, {"lens": "security"}, {"comment": "suggestion: Move it."},
                          {"line": 99}, {"found_by": []}, {"extra": "field"}):
            with self.subTest(overrides=overrides):
                result = self.finish([], [self.note(**overrides)])
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.artifacts / "review.md").exists())

    def test_clean_review_saves_an_empty_array(self):
        result = self.finish([])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.artifacts / "findings.json").read_text()), [])
        self.assertIn("No supported issues found.", result.stdout)

    def test_missing_quote_and_wrong_anchor_cannot_produce_final_artifacts(self):
        for overrides in ({"failure_scenario": "wrong result"}, {"line": 1}):
            with self.subTest(overrides=overrides):
                result = self.finish([self.finding(**overrides)])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("exact source quote", result.stderr)
                self.assertFalse((self.artifacts / "findings.json").exists())

    def test_output_inside_the_repository_is_rejected(self):
        (self.artifacts / "context.json").write_text(json.dumps({"repo_root": str(self.artifacts)}))
        result = self.finish([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the repository", result.stderr)
        self.assertFalse((self.artifacts / "findings.json").exists())


if __name__ == "__main__":
    unittest.main()
