import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_review.py"


class PrepareReviewTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="turtle-test-repo-")
        self.addCleanup(self.workspace.cleanup)
        self.repo = Path(self.workspace.name)
        self.git("init", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Review test")
        (self.repo / "example.txt").write_text("before\n")
        self.commit("initial")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.PIPE).decode().strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def review(self, target=None):
        status = self.git("status", "--porcelain")
        head = self.git("rev-parse", "HEAD")
        command = [sys.executable, str(SCRIPT)] + ([] if target is None else [target])
        result = subprocess.run(command, cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("status", "--porcelain"), status)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        context = json.loads(result.stdout)
        self.assertFalse(Path(context["diff_path"]).is_relative_to(self.repo))
        return context

    def test_commit_uses_exact_revision_and_root_commit_has_empty_before(self):
        initial = self.git("rev-parse", "HEAD")
        (self.repo / "example.txt").write_text("after\n")
        changed = self.commit("change")
        (self.repo / "example.txt").write_text("unrelated working copy\n")
        context = self.review(changed)
        self.assertEqual((Path(context["before_root"]) / "example.txt").read_text(), "before\n")
        self.assertEqual((Path(context["after_root"]) / "example.txt").read_text(), "after\n")
        root = self.review(initial)
        self.assertFalse(list(Path(root["before_root"]).iterdir()))
        self.assertIn("+before", Path(root["diff_path"]).read_text())

    def test_size_gate_counts_additions_and_deletions_at_fifty(self):
        (self.repo / "new.txt").write_text("new\n" * 49)
        small = self.commit("49 added lines")
        self.assertEqual(self.review(small)["mode"], "small")
        (self.repo / "new.txt").write_text("changed\n" * 25 + "new\n" * 24)
        full = self.commit("25 additions and 25 deletions")
        context = self.review(full)
        self.assertEqual(context["changed_lines"], 50)
        self.assertEqual(context["mode"], "full")

    def test_working_copy_includes_staged_and_unstaged_but_excludes_untracked(self):
        (self.repo / "staged.txt").write_text("staged\n")
        self.git("add", "staged.txt")
        (self.repo / "example.txt").write_text("unstaged\n")
        (self.repo / "untracked.txt").write_text("untracked\n")
        context = self.review()
        diff = Path(context["diff_path"]).read_text()
        self.assertIn("staged.txt", diff)
        self.assertIn("+unstaged", diff)
        self.assertNotIn("untracked.txt", diff)
        self.assertFalse((Path(context["after_root"]) / "untracked.txt").exists())
        scoped = self.review("path:example.txt")
        self.assertNotIn("staged.txt", Path(scoped["diff_path"]).read_text())

    def test_branch_uses_merge_base_and_ranges_compare_endpoints(self):
        base = self.git("rev-parse", "HEAD")
        self.git("switch", "-c", "feature")
        (self.repo / "feature.txt").write_text("feature\n")
        head = self.commit("feature")
        self.git("switch", "main")
        (self.repo / "main.txt").write_text("main\n")
        main = self.commit("main")
        context = self.review("feature")
        self.assertEqual(context["diff_range"], f"{base}..{head}")
        self.assertNotIn("main.txt", Path(context["diff_path"]).read_text())
        self.assertEqual(self.review(f"{main}...{head}")["diff_range"], f"{base}..{head}")
        self.assertEqual(self.review(f"{main}..{head}")["diff_range"], f"{main}..{head}")

    def test_binary_and_literal_symlink_snapshot(self):
        (self.repo / "binary.bin").write_bytes(b"\0binary")
        (self.repo / "link").symlink_to("/does/not/exist")
        commit = self.commit("binary and link")
        context = self.review(commit)
        self.assertEqual(context["mode"], "full")
        self.assertEqual(context["binary_files"], ["binary.bin"])
        link = Path(context["after_root"]) / "link"
        self.assertFalse(link.is_symlink())
        self.assertEqual(link.read_text(), "/does/not/exist")

    def test_path_review_includes_a_staged_deletion(self):
        self.git("rm", "example.txt")
        context = self.review("path:example.txt")
        self.assertIn("-before", Path(context["diff_path"]).read_text())
        self.assertFalse((Path(context["after_root"]) / "example.txt").exists())

    def test_temporary_directory_inside_repo_is_rejected_without_writing(self):
        import os

        temp = self.repo / "scratch"
        temp.mkdir()
        environment = dict(os.environ, TMPDIR=str(temp))
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=self.repo, env=environment, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the checkout", result.stderr)
        self.assertFalse(list(temp.iterdir()))

    def test_ambiguous_path_ref_requires_explicit_target_and_targets_are_data(self):
        self.git("branch", "example.txt")
        result = subprocess.run([sys.executable, str(SCRIPT), "example.txt"], cwd=self.repo, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("both a tracked path and a ref", result.stderr)
        self.assertTrue(self.review("path:example.txt")["empty"])
        name = "$(touch INJECTED).txt"
        (self.repo / name).write_text("literal\n")
        self.commit("literal path")
        (self.repo / name).write_text("changed\n")
        context = self.review("path:" + name)
        self.assertIn("+changed", Path(context["diff_path"]).read_text())
        self.assertFalse((self.repo / "INJECTED").exists())


    def test_unchanged_submodule_keeps_small_mode_and_changed_submodule_is_a_limit(self):
        head = self.git("rev-parse", "HEAD")
        self.git("update-index", "--add", "--cacheinfo", f"160000,{head},vendor")
        self.git("commit", "-m", "add submodule")
        (self.repo / "example.txt").write_text("after\n")
        self.git("commit", "-m", "small change", "--", "example.txt")
        unchanged = self.git("rev-parse", "HEAD")
        context = self.review(unchanged)
        self.assertEqual(context["unavailable_submodules"], [])
        self.assertEqual(context["mode"], "small")
        self.git("update-index", "--cacheinfo", f"160000,{unchanged},vendor")
        self.git("commit", "-m", "bump submodule")
        context = self.review(self.git("rev-parse", "HEAD"))
        self.assertEqual(context["unavailable_submodules"], ["vendor"])
        self.assertEqual(context["mode"], "full")

    def test_numeric_ref_requires_explicit_pr_or_commit_target(self):
        self.git("branch", "123")
        result = subprocess.run([sys.executable, str(SCRIPT), "123"], cwd=self.repo, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("both a PR number and a commit", result.stderr)
        self.assertTrue(self.review("commit:123")["diff_range"].endswith(self.git("rev-parse", "HEAD")))

    def test_path_with_dots_is_reviewed_as_a_path_not_a_range(self):
        name = "notes..v2.txt"
        (self.repo / name).write_text("one\n")
        self.commit("dotted path")
        (self.repo / name).write_text("two\n")
        context = self.review(name)
        self.assertEqual(context["scope"], name)
        self.assertIn("+two", Path(context["diff_path"]).read_text())
        result = subprocess.run([sys.executable, str(SCRIPT), "missing..nothing"], cwd=self.repo,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("range of existing commits", result.stderr)

if __name__ == "__main__":
    unittest.main()
