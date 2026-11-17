#!/usr/bin/env python3
"""Run an isolated turtle role or audit a native role's effective settings."""

import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
from types import SimpleNamespace


ROLES = {"summarizer": "summarizer", "bug-hunter": "finder", "security": "finder", "verifier": "verifier"}
POINTERS = {"diff_path", "before_root", "after_root", "repo_root", "schema_path", "diff_range", "scope", "mode",
            "binary_files", "unavailable_submodules"}
TOOLS = {"Read", "Grep", "Glob"}
DEFAULT_TIMEOUT = 1800


def shared_selector():
    path = Path(__file__).resolve().parents[2] / "model-selector" / "scripts" / "select_models.py"
    if not path.is_file():
        raise ValueError(f"missing shared model selector: {path}")
    return SimpleNamespace(**runpy.run_path(str(path)))


def payload(context, role, claim=None):
    result = {key: context[key] for key in POINTERS if key in context}
    if not POINTERS <= result.keys():
        raise ValueError("incomplete neutral review pointers")
    for key in ("diff_path", "before_root", "after_root", "repo_root", "schema_path"):
        if not Path(result[key]).is_absolute():
            raise ValueError(f"{key}: expected an absolute path")
    if role == "verifier":
        if not isinstance(claim, dict) or set(claim) != {"file", "line", "claim"}:
            raise ValueError("verifier requires only file, line, and claim")
        if (not isinstance(claim["file"], str) or not claim["file"] or Path(claim["file"]).is_absolute()
                or ".." in Path(claim["file"]).parts or type(claim["line"]) is not int or claim["line"] < 1
                or not isinstance(claim["claim"], str) or not claim["claim"].strip()):
            raise ValueError("invalid verifier claim")
        result["candidate"] = claim
    elif claim is not None:
        raise ValueError("only a verifier receives a claim")
    return result


def definition(role, model):
    path = Path(__file__).resolve().parents[3] / "agents" / f"turtle-{role}.md"
    source = path.read_text()
    _, frontmatter, body = source.split("---", 2)
    fields = dict(line.split(":", 1) for line in frontmatter.strip().splitlines())
    tools = {tool.strip() for tool in fields["tools"].split(",")}
    if tools != TOOLS:
        raise ValueError(f"{path}: expected the read-only turtle tool set")
    name = f"turtle-{role}"
    prompt = (body.strip() + "\n\nRead only the supplied diff_path and schema_path files and source under "
              "before_root, after_root, or repo_root. Set Grep and Glob paths to those source roots. "
              "Never search their parent directories or other review artifacts.")
    return {name: {"description": fields["description"].strip(), "prompt": prompt,
                   "tools": sorted(tools), "model": model}}


def verify_requests(requests, choice):
    expected_model = choice["resolved"]["model"]
    if not requests:
        raise ValueError("no effective request evidence; this CLI cannot verify model and effort")
    efforts = set()
    for request in requests:
        if request.get("model") != expected_model:
            raise ValueError("request evidence contains another model")
        names = {tool.get("name") for tool in request.get("tools", [])}
        if not names <= TOOLS | {"DeferredToolPlaceholder"}:
            raise ValueError("request evidence contains non-read-only tools")
        efforts.add(request.get("output_config", {}).get("effort"))
    if len(efforts) != 1:
        raise ValueError("runtime changed effort during the role")
    effective_effort = efforts.pop()
    expected_effort = choice["resolved"]["effort"]
    if expected_effort is not None and effective_effort != expected_effort:
        raise ValueError(f"effective effort mismatch: requested {expected_effort}; observed {effective_effort}")
    return {"agent": "claude", "model": expected_model, "effort": effective_effort}


def verify_runtime(directory, choice):
    events = [json.loads(line) for line in (directory / "runtime.jsonl").read_text().splitlines() if line.strip()]
    init = next((event for event in events if event.get("subtype") == "init"), None)
    if init is None or set(init.get("tools", [])) != TOOLS or init.get("mcp_servers") != []:
        raise ValueError("runtime did not preserve read-only tools and empty MCP configuration")
    content = json.loads((directory / "input.json").read_text())
    allowed = {str(Path(content[key]).resolve()) for key in ("repo_root", "before_root", "after_root")}
    if init.get("cwd") != str(directory.resolve()) or set(init.get("additional_directories", [])) != allowed:
        raise ValueError("runtime directory access differs from the isolated role scope")
    results = [event for event in events if event.get("type") == "result"]
    if not results or results[-1].get("is_error") or results[-1].get("permission_denials"):
        raise ValueError("role failed or a required tool was denied")
    expected_model = choice["resolved"]["model"]
    used = set(results[-1].get("modelUsage", {}))
    observed = {event["message"]["model"] for event in events if event.get("type") == "assistant"}
    if used != {expected_model} or observed != {expected_model} or init.get("model") != expected_model:
        raise ValueError(f"effective model mismatch: requested {expected_model}; observed {sorted(used | observed)}")
    session = init.get("session_id")
    if not session:
        raise ValueError("missing runtime session identity")
    trace = directory / "requests"
    records = [json.loads(line) for line in (trace / "index.jsonl").read_text().splitlines() if line.strip()]
    records = [record for record in records if record.get("session_id") == session]
    requests = []
    for record in records:
        response = json.loads((trace / record["response_file"]).read_text())
        if response.get("model") != expected_model:
            raise ValueError("response model differs from the approved choice")
        requests.append(json.loads((trace / record["request_file"]).read_text()))
    return verify_requests(requests, choice), results[-1]["result"]


def artifact_directory(context, prefix):
    root = Path(context["diff_path"]).resolve().parent
    repo = Path(context["repo_root"]).resolve()
    if root.is_relative_to(repo):
        raise ValueError("review artifacts must be outside the checkout")
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root))


def audit(policy_path, context_path, role, trace):
    selector = shared_selector()
    policy = selector.read_json(policy_path)
    if policy.get("profile") != "code-turtle":
        raise ValueError("expected an approved code-turtle policy")
    choice = policy["roles"][ROLES[role]]
    if choice["adapter"] != "claude-agent" or choice["resolved"]["agent"] != "claude":
        raise ValueError("native audit requires a selected Claude Agent route")
    context = selector.read_json(context_path)
    pointer = json.dumps(context["diff_path"])[1:-1]
    records = [json.loads(line) for line in (trace / "index.jsonl").read_text().splitlines() if line.strip()]
    records = [record for record in records
               if record.get("query_source") == f"agent:custom:ultrapowers:turtle-{role}"]
    requests = []
    matched = []
    for record in records:
        request = selector.read_json(trace / record["request_file"])
        if pointer not in json.dumps(request.get("messages", [])):
            continue
        response = selector.read_json(trace / record["response_file"])
        if response.get("model") != choice["resolved"]["model"]:
            raise ValueError("native response model differs from the approved choice")
        requests.append(request)
        matched.append(record)
    effective = verify_requests(requests, choice)
    directory = artifact_directory(context, f"{role}-audit-")
    evidence = {key: choice[key] for key in ("requested", "resolved", "inherited", "adapter")}
    evidence.update(effective=effective, complete=True, trace=str(trace.resolve()), records=matched)
    (directory / "selection.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return directory


def run(policy_path, context_path, role, claim_path=None, *, executable="claude", timeout=DEFAULT_TIMEOUT):
    if type(timeout) is not int or timeout < 1:
        raise ValueError("timeout must be a positive number of seconds")
    selector = shared_selector()
    policy = selector.read_json(policy_path)
    if policy.get("profile") != "code-turtle":
        raise ValueError("expected an approved code-turtle policy")
    choice = policy["roles"][ROLES[role]]
    if choice["adapter"] != "claude-cli" or choice["resolved"]["agent"] != "claude":
        raise ValueError("this adapter requires a selected Claude CLI route")
    if choice["launch"]["model"] != choice["resolved"]["model"]:
        raise ValueError("Claude CLI route requires an exact resolved ID")
    context = selector.read_json(context_path)
    content = payload(context, role, selector.read_json(claim_path) if claim_path else None)
    root = Path(context["diff_path"]).resolve().parent
    repo = Path(context["repo_root"]).resolve()
    allowed = [repo, Path(content["before_root"]).resolve(), Path(content["after_root"]).resolve()]
    if any(root.is_relative_to(path) for path in allowed):
        raise ValueError("role source access would expose the shared review artifacts")
    directory = artifact_directory(context, f"{role}-")
    for key, name in (("diff_path", "diff.patch"), ("schema_path", "finding-schema.md")):
        target = directory / name
        shutil.copyfile(content[key], target)
        content[key] = str(target)
    (directory / "input.json").write_text(json.dumps(content, indent=2) + "\n")
    defs = definition(role, choice["resolved"]["model"])
    (directory / "agents.json").write_text(json.dumps(defs, indent=2) + "\n")
    arguments = [executable, "-p", "--no-session-persistence", "--output-format", "stream-json", "--verbose",
                 "--agents", str(directory / "agents.json"), "--agent", f"turtle-{role}",
                 "--model", choice["launch"]["model"], "--tools", "Read,Grep,Glob",
                 "--allowedTools", "Read,Grep,Glob", "--strict-mcp-config", "--disable-slash-commands",
                 "--settings", json.dumps({"permissions": {"blockReadsOutsideWorkingDirectories": True}}),
                 "--permission-mode", "dontAsk", "--add-dir", *(str(path) for path in allowed)]
    if choice["launch"]["effort"] is not None:
        arguments += ["--effort", choice["launch"]["effort"]]
    env = os.environ.copy()
    env["OTEL_LOG_RAW_API_BODIES"] = "file:" + str(directory / "requests")
    evidence = {"requested": choice["requested"], "resolved": choice["resolved"], "inherited": choice["inherited"],
                "adapter": "claude-cli", "command": arguments, "timeout": timeout, "effective": None,
                "complete": False}
    try:
        with (directory / "runtime.jsonl").open("w") as stdout, (directory / "stderr.log").open("w") as stderr:
            process = subprocess.run(arguments, cwd=directory, env=env, input=json.dumps(content), text=True,
                                     stdout=stdout, stderr=stderr, timeout=timeout)
        if process.returncode:
            raise ValueError(f"Claude CLI exited {process.returncode}; see {directory / 'stderr.log'}")
        evidence["effective"], result = verify_runtime(directory, choice)
        (directory / "result.txt").write_text(result + "\n")
        evidence["complete"] = True
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        evidence["error"] = str(exc)
        raise ValueError(f"incomplete {role}: {exc}; artifacts: {directory}") from exc
    finally:
        (directory / "selection.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "audit"):
        command = commands.add_parser(name)
        command.add_argument("role", choices=ROLES)
        command.add_argument("--policy", required=True, type=Path)
        command.add_argument("--context", required=True, type=Path)
        if name == "run":
            command.add_argument("--claim", type=Path)
            command.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                                 help=f"seconds before the role is stopped (default {DEFAULT_TIMEOUT})")
        else:
            command.add_argument("--trace", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "run":
            print(run(args.policy, args.context, args.role, args.claim, timeout=args.timeout))
        else:
            print(audit(args.policy, args.context, args.role, args.trace))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"code-turtle: {exc}\n")


if __name__ == "__main__":
    main()
