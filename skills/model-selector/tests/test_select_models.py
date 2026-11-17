import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_models.py"
SPEC = importlib.util.spec_from_file_location("select_models", SCRIPT)
selector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selector)


def host():
    models = [
        {"id": "provider/a", "name": "a", "aliases": ["opus"], "efforts": ["high", "max"], "default_effort": "high"},
        {"id": "provider/b", "name": "b", "aliases": ["haiku"], "efforts": ["low", "high"], "default_effort": "low"},
        {"id": "provider/gpt-6.1-sol", "name": "gpt-6.1-sol", "aliases": [], "efforts": ["high", "max"], "default_effort": "high"},
        {"id": "provider/gpt-6.1-terra", "name": "gpt-6.1-terra", "aliases": [], "efforts": ["high", "max"], "default_effort": "high"},
    ]
    return {"session_agent": "claude", "agents": {
        "claude": {"default_model": "provider/a", "default_effort": "max", "provider": "provider",
                   "models": models, "evidence": "verified session and catalog",
                   "adapters": [
                       {"id": "claude-agent", "models": ["alias", "inherit"], "effort": True, "evidence": "Agent schema"},
                       {"id": "claude-cli", "models": ["id"], "effort": True, "evidence": "CLI probe"},
                   ]},
        "codex": {"default_model": "provider/gpt-6.1-sol", "default_effort": "high", "provider": "provider",
                  "models": models, "evidence": "CLI catalog",
                  "adapters": [{"id": "orca", "models": ["id", "inherit"], "effort": True, "evidence": "Orca launch receipt"}]},
    }}


def choice(model=None, effort=None, agent=None):
    return {"agent": agent, "model": model, "effort": effort}


class SelectorTests(unittest.TestCase):
    def setUp(self):
        self.host = host()
        self.config = selector.load_config()

    def test_defaults_preserve_both_callers(self):
        turtle = selector.select(self.config, "code-turtle", self.host)
        self.assertEqual(turtle["roles"]["summarizer"]["launch"], {"model": "haiku", "effort": None})
        for role in ("finder", "verifier"):
            result = turtle["roles"][role]
            self.assertEqual(result["launch"], {"model": None, "effort": None})
            self.assertEqual(result["inherited"], ["agent", "effort", "model"])
            self.assertEqual(result["resolved"], {"agent": "claude", "model": "provider/a", "effort": "max"})
            self.assertIsNone(result["effective"])
        orca = selector.select(self.config, "orca-poteto", self.host)
        self.assertEqual(orca["roles"]["implementation"]["resolved"]["model"], "provider/gpt-6.1-sol")
        self.assertEqual(orca["roles"]["review"][0]["resolved"]["effort"], "max")
        self.assertEqual(orca["review_budget"], 2)

    def test_full_id_uses_cli_and_keeps_exact_effort(self):
        result = selector.select(self.config, "code-turtle", self.host,
                                 {"roles": {"verifier": {"model": "provider/b", "effort": "high"}}})
        selected = result["roles"]["verifier"]
        self.assertEqual(selected["adapter"], "claude-cli")
        self.assertEqual(selected["launch"], {"model": "provider/b", "effort": "high"})
        self.assertEqual(selected["inherited"], ["agent"])

    def test_field_overrides_do_not_change_other_defaults_or_config(self):
        before = copy.deepcopy(self.config)
        result = selector.select(self.config, "orca-poteto", self.host,
                                 {"roles": {"implementation": {"effort": "max"}}})
        self.assertEqual(result["roles"]["implementation"]["requested"],
                         choice("gpt-6.1-sol", "max", "codex"))
        self.assertEqual(self.config, before)

    def test_explicit_effort_resolves_inherited_model_for_orca_flag(self):
        result = selector.resolve(choice(effort="max", agent="codex"), self.host)
        self.assertEqual(result["launch"], {"model": "provider/gpt-6.1-sol", "effort": "max"})
        self.assertEqual(result["inherited"], ["model"])

    def test_native_adapter_does_not_change_runtime(self):
        self.host["agents"]["codex"]["adapters"][0]["id"] = "native"
        result = selector.resolve(choice("provider/b", "high", "codex"), self.host)
        self.assertEqual(result["resolved"]["agent"], "codex")
        self.assertEqual(result["adapter"], "native")

    def test_no_substring_version_or_variant_substitution(self):
        for name in ("provid/a", "provider/missing", "gpt-6.1", "gpt-6.1-sol-mini", "B"):
            with self.subTest(name=name), self.assertRaises(selector.SelectionError):
                selector.resolve(choice(name), self.host)

    def test_ambiguity_has_no_bare_id_priority(self):
        info = self.host["agents"]["claude"]
        info["provider"] = None
        info["models"].append(dict(info["models"][0], id="a", aliases=[]))
        with self.assertRaises(selector.SelectionError):
            selector.resolve(choice("a"), self.host)
        info["provider"] = "provider"
        self.assertEqual(selector.resolve(choice("a"), self.host)["resolved"]["model"], "provider/a")
        self.assertEqual(selector.resolve(choice("provider/a"), self.host)["resolved"]["model"], "provider/a")

    def test_missing_runtime_and_effort_stop_without_substitution(self):
        for entry in (choice("provider/b", "max"), choice("provider/a", "max", "grok")):
            with self.subTest(entry=entry), self.assertRaises(selector.SelectionError):
                selector.resolve(entry, self.host)

    def test_agent_tool_cannot_accept_full_id_or_unsupported_effort(self):
        info = self.host["agents"]["claude"]
        info["adapters"] = info["adapters"][:1]
        with self.assertRaises(selector.SelectionError):
            selector.resolve(choice("provider/a"), self.host)
        info["adapters"][0]["effort"] = False
        with self.assertRaises(selector.SelectionError):
            selector.resolve(choice("opus", "max"), self.host)

    def test_cli_pins_parent_inheritance_without_claiming_override(self):
        self.host["agents"]["claude"]["adapters"].pop(0)
        result = selector.resolve(choice(), self.host)
        self.assertEqual(result["launch"], {"model": "provider/a", "effort": "max"})
        self.assertEqual(result["requested"], choice())
        self.assertEqual(result["inherited"], ["agent", "effort", "model"])

    def test_host_discovery_requires_catalog_and_adapter_evidence(self):
        cases = []
        for mutate in (
            lambda h: h["agents"]["claude"].update(evidence=""),
            lambda h: h["agents"]["claude"].update(default_model="missing"),
            lambda h: h["agents"]["claude"]["adapters"][0].update(models=["id"]),
            lambda h: h["agents"]["codex"]["adapters"][0].update(id="claude-cli", models=["id"]),
        ):
            value = host()
            mutate(value)
            cases.append(value)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(selector.SelectionError):
                selector.select(self.config, "code-turtle", value)

    def test_strict_config_rejects_missing_unknown_duplicate_and_empty_values(self):
        cases = []
        for mutate in (
            lambda c: c["orca-poteto"]["roles"]["implementation"].pop("effort"),
            lambda c: c["orca-poteto"].update(extra=True),
            lambda c: c["orca-poteto"]["roles"].update(review=[]),
            lambda c: c["code-turtle"]["roles"]["finder"].update(model=""),
            lambda c: c["orca-poteto"].update(review_budget=True),
            lambda c: c["code-turtle"].update(review_budget=2),
            lambda c: c["orca-poteto"].update(ranking_source="file:///private"),
            lambda c: c["orca-poteto"]["roles"]["implementation"].update(agent=None),
        ):
            value = copy.deepcopy(self.config)
            mutate(value)
            cases.append(json.dumps(value))
        cases.append('{"orca-poteto":{},"orca-poteto":{}}')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for value in cases:
                path.write_text(value)
                with self.subTest(value=value), self.assertRaises(selector.SelectionError):
                    selector.load_config(path)
            with self.assertRaises(selector.SelectionError):
                selector.load_config(path.parent / "absent.json")

    def test_invalid_overrides_cannot_turn_errors_into_inheritance(self):
        for override in ({"roles": {"unknown": {}}}, {"roles": {"finder": {"model": ""}}},
                         {"roles": {"verifier": {"runtime": "codex"}}}, {"review_budget": False}, [], False):
            with self.subTest(override=override), self.assertRaises(selector.SelectionError):
                selector.select(self.config, "code-turtle", self.host, override)

    def test_directory_symlink_and_plugin_paths_work_outside_repo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = root / "host.json"
            host_path.write_text(json.dumps(self.host))
            link = root / "model-selector"
            link.symlink_to(SCRIPT.parents[1], target_is_directory=True)
            for script in (SCRIPT, link / "scripts" / SCRIPT.name):
                result = subprocess.run(["python3", "-B", str(script), "code-turtle", "--host", str(host_path)],
                                        cwd=root, capture_output=True, text=True, check=True)
                self.assertEqual(json.loads(result.stdout)["roles"]["summarizer"]["launch"]["model"], "haiku")


if __name__ == "__main__":
    unittest.main()
