#!/usr/bin/env python3
"""Validate shared defaults and resolve choices against verified launch capabilities."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


class SelectionError(ValueError):
    pass


PROFILES = {
    "orca-poteto": {"implementation", "review"},
    "code-turtle": {"summarizer", "finder", "verifier"},
}
ADAPTERS = {"orca", "native", "claude-agent", "claude-cli"}
FIELDS = {"agent", "model", "effort"}


def require(condition, message):
    if not condition:
        raise SelectionError(message)


def keys(value, expected, where):
    require(isinstance(value, dict) and set(value) == expected,
            f"{where}: expected exactly {sorted(expected)}")


def text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate key: {key}")
        result[key] = value
    return result


def read_json(path):
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)
    except (OSError, ValueError) as exc:
        raise SelectionError(f"{path}: {exc}") from exc


def validate_entry(entry, where, *, partial=False, inherit_agent=True):
    require(isinstance(entry, dict), f"{where}: expected an object")
    if partial:
        require(set(entry) <= FIELDS, f"{where}: unknown fields")
    else:
        keys(entry, FIELDS, where)
    for field, value in entry.items():
        require(value is None or text(value), f"{where}.{field}: expected text or null")
    require(inherit_agent or entry.get("agent") is not None,
            f"{where}.agent: must select a runtime")


def load_config(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / "models.json"
    config = read_json(path)
    keys(config, set(PROFILES), str(path))
    for profile, roles in PROFILES.items():
        value = config[profile]
        keys(value, {"roles", "review_budget", "ranking_source"}, profile)
        keys(value["roles"], roles, f"{profile}.roles")
        budget = value["review_budget"]
        require(budget is None or (type(budget) is int and budget > 0),
                f"{profile}.review_budget: expected positive integer or null")
        source = value["ranking_source"]
        require(source is None or (text(source) and urlparse(source).scheme in {"http", "https"}
                                   and bool(urlparse(source).netloc)),
                f"{profile}.ranking_source: expected public URL or null")
        for role, entries in value["roles"].items():
            if role == "review":
                require(isinstance(entries, list) and bool(entries), f"{profile}.review: empty list")
            else:
                entries = [entries]
            for entry in entries:
                validate_entry(entry, f"{profile}.{role}", inherit_agent=profile != "orca-poteto")
    return config


def validate_host(host):
    keys(host, {"session_agent", "agents"}, "host")
    require(text(host["session_agent"]), "host.session_agent: required")
    require(isinstance(host["agents"], dict) and host["agents"], "host.agents: required")
    require(host["session_agent"] in host["agents"], "session runtime missing from host")
    for agent, info in host["agents"].items():
        require(text(agent), "invalid agent ID")
        keys(info, {"default_model", "default_effort", "provider", "models", "adapters", "evidence"}, agent)
        require(text(info["evidence"]), f"{agent}: missing discovery evidence")
        require(info["provider"] is None or text(info["provider"]), f"{agent}: invalid provider")
        require(text(info["default_model"]), f"{agent}: missing exact default model")
        require(info["default_effort"] is None or text(info["default_effort"]), f"{agent}: invalid default effort")
        require(isinstance(info["models"], list) and info["models"], f"{agent}: empty catalog")
        ids = set()
        for model in info["models"]:
            keys(model, {"id", "name", "aliases", "efforts", "default_effort"}, f"{agent}.model")
            require(text(model["id"]) and model["id"] not in ids, f"{agent}: duplicate/invalid model ID")
            ids.add(model["id"])
            require(text(model["name"]), f"{agent}: invalid model name")
            for field in ("aliases", "efforts"):
                values = model[field]
                require(isinstance(values, list) and all(text(v) for v in values)
                        and len(set(values)) == len(values), f"{agent}: invalid {field}")
            require(model["default_effort"] is None or model["default_effort"] in model["efforts"],
                    f"{agent}: unsupported model default effort")
        require(info["default_model"] in ids, f"{agent}: default missing from catalog")
        default = next(m for m in info["models"] if m["id"] == info["default_model"])
        require(info["default_effort"] is None or info["default_effort"] in default["efforts"],
                f"{agent}: unsupported runtime default effort")
        require(isinstance(info["adapters"], list) and info["adapters"], f"{agent}: no launch adapter")
        adapter_ids = set()
        for adapter in info["adapters"]:
            keys(adapter, {"id", "models", "effort", "evidence"}, f"{agent}.adapter")
            require(adapter["id"] in ADAPTERS and adapter["id"] not in adapter_ids,
                    f"{agent}: unknown/duplicate adapter")
            adapter_ids.add(adapter["id"])
            modes = adapter["models"]
            require(isinstance(modes, list) and modes and set(modes) <= {"id", "alias", "inherit"},
                    f"{agent}: invalid adapter model modes")
            require(type(adapter["effort"]) is bool and text(adapter["evidence"]),
                    f"{agent}: unverified launch adapter")
            if adapter["id"].startswith("claude-"):
                require(agent == "claude", "Claude adapter cannot switch runtimes")
            if adapter["id"] == "claude-agent":
                require("id" not in modes, "Agent.model cannot accept full IDs")
            if adapter["id"] == "claude-cli":
                require(modes == ["id"], "Claude CLI pins exact IDs")


def resolve(entry, host):
    validate_entry(entry, "choice")
    agent = entry["agent"] or host["session_agent"]
    require(agent in host["agents"], f"unavailable runtime: {agent}")
    info = host["agents"][agent]
    requested_model = entry["model"]
    name = requested_model or info["default_model"]
    models = info["models"]
    exact = [m for m in models if m["id"] == name]
    if "/" in name or requested_model is None:
        matches = exact
    else:
        matches = [m for m in models if m["id"] == name or m["name"] == name
                   or name in m["aliases"]]
        if len(matches) > 1 and info["provider"]:
            preferred = [m for m in matches if m["id"].rsplit("/", 1)[0] == info["provider"]]
            if preferred:
                matches = preferred
    require(len(matches) == 1, f"model {name!r}: expected one exact match; candidates: "
            + ", ".join(m["id"] for m in matches))
    model = matches[0]
    effort = entry["effort"]
    require(effort is None or effort in model["efforts"], f"{model['id']}: unsupported effort {effort}")
    resolved_effort = effort
    if effort is None:
        resolved_effort = info["default_effort"] if requested_model is None else model["default_effort"]
    mode = "inherit" if requested_model is None else "alias" if name in model["aliases"] else "id"
    for adapter in info["adapters"]:
        launch_mode = mode
        if mode not in adapter["models"]:
            if "id" not in adapter["models"]:
                continue
            launch_mode = "id"
        if effort is not None and not adapter["effort"]:
            continue
        if adapter["id"] == "claude-agent" and mode == "alias" and name not in {"haiku", "sonnet", "opus", "fable"}:
            continue
        launch_model = None if launch_mode == "inherit" else name if launch_mode == "alias" else model["id"]
        if effort is not None and launch_model is None and adapter["id"] == "orca":
            launch_model = model["id"]
        launch_effort = effort
        if adapter["id"] == "claude-cli":
            require(resolved_effort is not None or effort is None,
                    "Claude CLI cannot pin unverified effort")
            launch_effort = resolved_effort
        return {
            "requested": entry.copy(),
            "resolved": {"agent": agent, "model": model["id"], "effort": resolved_effort},
            "inherited": sorted(k for k, v in entry.items() if v is None),
            "adapter": adapter["id"],
            "launch": {"model": launch_model, "effort": launch_effort},
            "evidence": [info["evidence"], adapter["evidence"]],
            "effective": None,
        }
    raise SelectionError(f"{agent}/{name}/{effort}: no verified adapter can honor this choice")


def select(config, profile, host, overrides=None):
    require(profile in PROFILES, f"unknown profile: {profile}")
    validate_host(host)
    policy = config[profile]
    overrides = overrides or {}
    require(isinstance(overrides, dict) and set(overrides) <= {"roles", "review_budget", "ranking_source"},
            "unknown override fields")
    role_overrides = overrides.get("roles", {})
    require(isinstance(role_overrides, dict) and set(role_overrides) <= PROFILES[profile], "unknown role overrides")
    merged = json.loads(json.dumps(policy))
    for role, value in role_overrides.items():
        if role == "review":
            require(isinstance(value, list) and value, "review override must be a nonempty list")
            for entry in value:
                validate_entry(entry, "review override", inherit_agent=False)
            merged["roles"][role] = value
        else:
            validate_entry(value, f"{role} override", partial=True)
            merged["roles"][role].update(value)
    for field in ("review_budget", "ranking_source"):
        if field in overrides:
            merged[field] = overrides[field]
    validation = dict(config, **{profile: merged})
    # Use the same validation for defaults and merged overrides.
    validate_config = json.dumps(validation)
    validate_config = json.loads(validate_config)
    budget = merged["review_budget"]
    require(budget is None or (type(budget) is int and budget > 0), "invalid review_budget override")
    source = merged["ranking_source"]
    require(source is None or (text(source) and urlparse(source).scheme in {"http", "https"}
                               and bool(urlparse(source).netloc)), "invalid ranking_source override")
    resolved = {}
    for role, value in merged["roles"].items():
        entries = value if role == "review" else [value]
        for entry in entries:
            validate_entry(entry, role, inherit_agent=profile != "orca-poteto")
        choices = [resolve(entry, host) for entry in entries]
        resolved[role] = choices if role == "review" else choices[0]
    return {"profile": profile, "roles": resolved, "review_budget": budget, "ranking_source": source}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("--host", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--overrides", type=Path)
    args = parser.parse_args()
    try:
        result = select(load_config(args.config), args.profile, read_json(args.host),
                        read_json(args.overrides) if args.overrides else None)
    except (SelectionError, TypeError) as exc:
        parser.exit(2, f"model selection stopped: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
