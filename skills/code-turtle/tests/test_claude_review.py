import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "claude_review.py"
SPEC = importlib.util.spec_from_file_location("claude_review", SCRIPT)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.context = {"repo_root": str(self.repo), "diff_path": str(self.artifacts / "diff.patch"),
                        "before_root": str(self.artifacts / "before"), "after_root": str(self.artifacts / "after"),
                        "schema_path": str(self.artifacts / "schema.md"), "diff_range": "base..head", "scope": "all",
                        "mode": "small", "binary_files": [], "unavailable_submodules": [],
                        "summary": "must not enter child context", "candidate_arrays": ["another claim"]}
        self.context_path = self.artifacts / "context.json"
        self.context_path.write_text(json.dumps(self.context))
        Path(self.context["diff_path"]).write_text("neutral diff\n")
        Path(self.context["schema_path"]).write_text("neutral schema\n")
        Path(self.context["before_root"]).mkdir()
        Path(self.context["after_root"]).mkdir()
        self.choice = {"requested": {"agent": None, "model": "provider/selected", "effort": "high"},
                       "resolved": {"agent": "claude", "model": "provider/selected", "effort": "high"},
                       "inherited": ["agent"], "adapter": "claude-cli",
                       "launch": {"model": "provider/selected", "effort": "high"}}
        self.policy_path = self.artifacts / "policy.json"
        self.policy_path.write_text(json.dumps({"profile": "code-turtle", "roles": {
            "summarizer": self.choice, "finder": self.choice, "verifier": self.choice}}))
        self.fake = self.root / "claude"
        self.fake.write_text('''#!/usr/bin/env python3
import json, os
from pathlib import Path
import sys
args = sys.argv
model = args[args.index('--model') + 1]
effort = args[args.index('--effort') + 1] if '--effort' in args else 'high'
assert json.loads(args[args.index('--settings') + 1])['permissions']['blockReadsOutsideWorkingDirectories'] is True
start = args.index('--add-dir') + 1
end = next((i for i in range(start, len(args)) if args[i].startswith('--')), len(args))
allowed = args[start:end]
definition = json.loads(Path(args[args.index('--agents') + 1]).read_text())
name = args[args.index('--agent') + 1]
assert definition[name]['tools'] == ['Glob','Grep','Read']
assert definition[name]['model'] == model
assert args[args.index('--tools') + 1] == 'Read,Grep,Glob'
assert args[args.index('--allowedTools') + 1] == 'Read,Grep,Glob'
assert '--strict-mcp-config' in args and '--disable-slash-commands' in args
assert '--resume' not in args
Path('received.json').write_text(sys.stdin.read())
requests = Path(os.environ['OTEL_LOG_RAW_API_BODIES'].removeprefix('file:'))
requests.mkdir()
(requests / 'turn.request.json').write_text(json.dumps({'model': model, 'output_config': {'effort': effort},
    'tools': [{'name': t} for t in ['Read','Grep','Glob']]}))
(requests / 'turn.response.json').write_text(json.dumps({'model':model}))
(requests / 'index.jsonl').write_text(json.dumps({'session_id':'child-session',
    'request_file':'turn.request.json','response_file':'turn.response.json'}))
print(json.dumps({'type':'system','subtype':'init','session_id':'child-session','model':model,
    'tools':['Read','Grep','Glob'],'mcp_servers':[], 'cwd':str(Path.cwd()),'additional_directories':allowed}))
print(json.dumps({'type':'assistant','message':{'model':model}}))
print(json.dumps({'type':'result','is_error':False,'modelUsage':{model:{}},'permission_denials':[],
    'result':'{"verdict":"rejected","evidence":"independent static counterexample"}'}))
''')
        self.fake.chmod(0o700)

    def test_clean_verifier_dispatch_and_effective_evidence(self):
        claim = {"file": "file.py", "line": 3, "claim": "One exact claim"}
        claim_path = self.artifacts / "claim.json"
        claim_path.write_text(json.dumps(claim))
        directory = adapter.run(self.policy_path, self.context_path, "verifier", claim_path, executable=str(self.fake))
        received = json.loads((directory / "received.json").read_text())
        self.assertEqual(set(received), adapter.POINTERS | {"candidate"})
        self.assertEqual(received["candidate"], claim)
        self.assertEqual(Path(received["diff_path"]).parent, directory)
        self.assertEqual(Path(received["schema_path"]).parent, directory)
        self.assertEqual(Path(received["diff_path"]).read_text(), "neutral diff\n")
        self.assertEqual(Path(received["schema_path"]).read_text(), "neutral schema\n")
        evidence = json.loads((directory / "selection.json").read_text())
        command = evidence["command"]
        start = command.index("--add-dir") + 1
        end = next((i for i in range(start, len(command)) if command[i].startswith("--")), len(command))
        allowed = command[start:end]
        self.assertEqual(set(allowed), {str(self.repo), self.context["before_root"], self.context["after_root"]})
        self.assertNotIn(str(self.artifacts), allowed)
        self.assertTrue(evidence["complete"])
        self.assertEqual(evidence["effective"], self.choice["resolved"])
        self.assertEqual(evidence["inherited"], ["agent"])
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_inherited_effort_keeps_scope_and_observed_effort(self):
        policy = json.loads(self.policy_path.read_text())
        choice = policy["roles"]["finder"]
        choice["requested"]["effort"] = choice["resolved"]["effort"] = choice["launch"]["effort"] = None
        choice["inherited"].append("effort")
        self.policy_path.write_text(json.dumps(policy))
        directory = adapter.run(self.policy_path, self.context_path, "bug-hunter", executable=str(self.fake))
        evidence = json.loads((directory / "selection.json").read_text())
        self.assertTrue(evidence["complete"])
        self.assertNotIn("--effort", evidence["command"])
        self.assertEqual(evidence["effective"]["effort"], "high")
        self.assertIn("effort", evidence["inherited"])

    def test_source_scope_cannot_include_shared_artifacts(self):
        for key in ("repo_root", "before_root", "after_root"):
            context = copy.deepcopy(self.context)
            context[key] = str(self.root)
            self.context_path.write_text(json.dumps(context))
            with self.subTest(key=key), self.assertRaises(ValueError):
                adapter.run(self.policy_path, self.context_path, "bug-hunter", executable=str(self.fake))
        self.assertEqual(list(self.artifacts.glob("bug-hunter-*")), [])

    def test_verifier_rejects_full_candidate_input(self):
        claim = {"file": "file.py", "line": 3, "claim": "One exact claim", "severity": "blocking"}
        with self.assertRaises(ValueError):
            adapter.payload(self.context, "verifier", claim)
        with self.assertRaises(ValueError):
            adapter.payload(self.context, "bug-hunter", {"file": "file.py", "line": 1, "claim": "x"})

    def test_native_choice_is_never_relaunched_as_cli(self):
        policy = json.loads(self.policy_path.read_text())
        policy["roles"]["finder"]["adapter"] = "claude-agent"
        self.policy_path.write_text(json.dumps(policy))
        with self.assertRaises(ValueError):
            adapter.run(self.policy_path, self.context_path, "bug-hunter", executable=str(self.fake))
        self.assertEqual(sorted(path.name for path in self.artifacts.iterdir()),
                         ["after", "before", "context.json", "diff.patch", "policy.json", "schema.md"])

    def runtime_fixture(self):
        directory = self.root / "runtime"
        directory.mkdir()
        requests = directory / "requests"
        requests.mkdir()
        (directory / "input.json").write_text(json.dumps(self.context))
        self.events = [
            {"type": "system", "subtype": "init", "session_id": "child-session", "model": "provider/selected",
             "tools": ["Read", "Grep", "Glob"], "mcp_servers": [], "cwd": str(directory),
             "additional_directories": [self.context[key] for key in ("repo_root", "before_root", "after_root")]},
            {"type": "assistant", "message": {"model": "provider/selected"}},
            {"type": "result", "is_error": False, "modelUsage": {"provider/selected": {}}, "permission_denials": [], "result": "[]"},
        ]
        self.request = {"model": "provider/selected", "tools": [{"name": "Read"}], "output_config": {"effort": "high"}}
        return directory

    def write_runtime(self, directory, events, request):
        (directory / "runtime.jsonl").write_text("\n".join(json.dumps(e) for e in events))
        (directory / "requests" / "turn.request.json").write_text(json.dumps(request))
        (directory / "requests" / "turn.response.json").write_text(json.dumps({"model": "provider/selected"}))
        (directory / "requests" / "index.jsonl").write_text(json.dumps({"session_id": "child-session",
            "query_source": "agent:custom:ultrapowers:turtle-verifier",
            "request_file": "turn.request.json", "response_file": "turn.response.json"}))

    def test_requested_flags_without_observed_evidence_cannot_pass(self):
        directory = self.runtime_fixture()
        self.write_runtime(directory, self.events, self.request)
        (directory / "requests" / "turn.request.json").unlink()
        with self.assertRaises((ValueError, OSError)):
            adapter.verify_runtime(directory, self.choice)

    def test_model_effort_tool_and_denied_read_mismatches_are_incomplete(self):
        directory = self.runtime_fixture()
        mutations = [
            lambda events, request: events[-1].update(modelUsage={"provider/fallback": {}}),
            lambda events, request: events[1]["message"].update(model="provider/fallback"),
            lambda events, request: events[0]["tools"].append("Bash"),
            lambda events, request: events[0].pop("mcp_servers"),
            lambda events, request: events[0].pop("session_id"),
            lambda events, request: events[0].pop("additional_directories"),
            lambda events, request: events[0]["additional_directories"].append(str(self.artifacts)),
            lambda events, request: events[0].update(cwd=str(self.artifacts)),
            lambda events, request: events[-1]["permission_denials"].append({"tool_name": "Read"}),
            lambda events, request: request["output_config"].update(effort="max"),
            lambda events, request: request.update(model="provider/fallback"),
            lambda events, request: request["tools"].append({"name": "Agent"}),
        ]
        for mutate in mutations:
            events, request = copy.deepcopy(self.events), copy.deepcopy(self.request)
            mutate(events, request)
            self.write_runtime(directory, events, request)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                adapter.verify_runtime(directory, self.choice)

    def test_raw_response_and_session_mismatches_cannot_pass(self):
        directory = self.runtime_fixture()
        self.write_runtime(directory, self.events, self.request)
        (directory / "requests" / "turn.response.json").write_text(json.dumps({"model": "provider/fallback"}))
        with self.assertRaises(ValueError):
            adapter.verify_runtime(directory, self.choice)
        self.write_runtime(directory, self.events, self.request)
        (directory / "requests" / "index.jsonl").write_text(json.dumps({"session_id": "another-session",
            "request_file": "turn.request.json", "response_file": "turn.response.json"}))
        with self.assertRaises(ValueError):
            adapter.verify_runtime(directory, self.choice)
        (directory / "requests" / "index.jsonl").write_text("")
        with self.assertRaises(ValueError):
            adapter.verify_runtime(directory, self.choice)

    def test_failed_cli_saves_incomplete_record(self):
        self.fake.write_text('#!/bin/sh\nexit 9\n')
        with self.assertRaises(ValueError):
            adapter.run(self.policy_path, self.context_path, "bug-hunter", executable=str(self.fake))
        records = list(self.artifacts.glob("bug-hunter-*/selection.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text())
        self.assertFalse(record["complete"])
        self.assertIsNone(record["effective"])

    def test_native_audit_uses_actual_role_requests_and_responses(self):
        directory = self.runtime_fixture()
        self.request["messages"] = [{"role": "user", "content": self.context["diff_path"]}]
        self.write_runtime(directory, self.events, self.request)
        index = directory / "requests" / "index.jsonl"
        policy = json.loads(self.policy_path.read_text())
        policy["roles"]["verifier"]["adapter"] = "claude-agent"
        self.policy_path.write_text(json.dumps(policy))
        result = adapter.audit(self.policy_path, self.context_path, "verifier", directory / "requests")
        evidence = json.loads((result / "selection.json").read_text())
        self.assertEqual(evidence["effective"], self.choice["resolved"])
        self.assertTrue(evidence["complete"])
        original = copy.deepcopy(self.request)
        self.request["messages"] = [{"role": "user", "content": "/another/review/diff.patch"}]
        self.write_runtime(directory, self.events, self.request)
        with self.assertRaises(ValueError):
            adapter.audit(self.policy_path, self.context_path, "verifier", directory / "requests")
        self.write_runtime(directory, self.events, original)
        (directory / "requests" / "turn.response.json").write_text(json.dumps({"model": "provider/fallback"}))
        with self.assertRaises(ValueError):
            adapter.audit(self.policy_path, self.context_path, "verifier", directory / "requests")
        index.write_text("")
        with self.assertRaises(ValueError):
            adapter.audit(self.policy_path, self.context_path, "verifier", directory / "requests")

    def test_symlink_resolves_shared_dependency_and_missing_copy_stops(self):
        linked = self.root / "linked-turtle"
        linked.symlink_to(SCRIPT.parents[1], target_is_directory=True)
        spec = importlib.util.spec_from_file_location("linked_adapter", linked / "scripts" / SCRIPT.name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIn("code-turtle", module.shared_selector().load_config())
        isolated = self.root / "skills" / "code-turtle" / "scripts"
        isolated.mkdir(parents=True)
        shutil.copyfile(SCRIPT, isolated / SCRIPT.name)
        spec = importlib.util.spec_from_file_location("missing_adapter", isolated / SCRIPT.name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(ValueError):
            module.shared_selector()


if __name__ == "__main__":
    unittest.main()
