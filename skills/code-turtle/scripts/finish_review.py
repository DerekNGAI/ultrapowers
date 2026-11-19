#!/usr/bin/env python3
import json
from pathlib import Path, PurePosixPath
import re
import sys


FIELDS = {"file", "line", "severity", "lens", "claim", "failure_scenario", "comment", "verdict", "found_by"}
NOTE_FIELDS = {"file", "line", "lens", "note", "comment", "second_opinion", "found_by"}
SEVERITY = {"blocking": 0, "should-fix": 1, "minor": 2}
VERDICT = {"confirmed": 0, "plausible": 1}
OPINION = {"agree": 0, "partly": 1}
LENSES = {"correctness", "security", "data", "performance"}
NOTE_LENSES = {"design", "data", "performance"}
NOTE_PREFIX = "suggestion (non-blocking):"


def check_shape(item, label, fields):
    if not isinstance(item, dict) or set(item) != fields:
        raise ValueError(f"{label} must have exactly {sorted(fields)}.")
    if type(item["line"]) is not int or item["line"] < 1:
        raise ValueError(f"{label} needs a positive integer line.")
    if any(not isinstance(item[key], str) or not item[key].strip() for key in fields - {"line", "found_by"}):
        raise ValueError(f"{label} has an empty or non-string field.")
    found_by = item["found_by"]
    if not isinstance(found_by, list) or not found_by or any(not isinstance(model, str) or not model.strip() for model in found_by) or len(set(found_by)) != len(found_by):
        raise ValueError(f"{label} needs found_by as a nonempty list of distinct model labels.")
    path = PurePosixPath(item["file"])
    if path.is_absolute() or ".." in path.parts or str(path) == ".":
        raise ValueError(f"{label} needs a repository-relative file.")


def anchors(context, item):
    for key in ("before_root", "after_root"):
        source = Path(context[key]) / item["file"]
        if source.is_file():
            lines = source.read_text(errors="replace").splitlines()
            if len(lines) >= item["line"]:
                yield lines[item["line"] - 1].strip()


def merge(items, identity, rank):
    unique = {}
    for item in sorted(items, key=rank):
        kept = unique.setdefault(identity(item), item)
        kept["found_by"] = list(dict.fromkeys(kept["found_by"] + item["found_by"]))
    return sorted(unique.values(), key=rank)


def render(heading, item, keys):
    fields = "\n".join(f"- **{key}:** {item[key]}" for key in keys)
    fields += f"\n- **found_by:** {', '.join(item['found_by'])}"
    fence = "`" * max(3, max((len(part) for part in re.findall(r"`+", item["comment"])), default=0) + 1)
    return f"### {heading}\n\n{fields}\n\n**comment:**\n\n{fence}\n{item['comment']}\n{fence}"


def finish(artifact_directory):
    directory = Path(artifact_directory).resolve()
    context = json.loads((directory / "context.json").read_text())
    repo = Path(context["repo_root"]).resolve()
    for name in ("findings.json", "notes.json", "review.md"):
        if (directory / name).resolve().is_relative_to(repo):
            raise ValueError("Review output must be outside the repository.")
    summary = (directory / "summary.md").read_text().strip()
    if not summary:
        raise ValueError("summary.md must contain the plain-language summary.")
    findings = json.loads((directory / "reviewed-findings.json").read_text())
    if not isinstance(findings, list):
        raise ValueError("reviewed-findings.json must be an array.")
    for index, finding in enumerate(findings, 1):
        check_shape(finding, f"Issue {index}", FIELDS)
        if finding["severity"] not in SEVERITY or finding["verdict"] not in VERDICT:
            raise ValueError(f"Issue {index} needs a supported severity and a surviving verdict.")
        if finding["lens"] not in LENSES:
            raise ValueError(f"Issue {index} needs a lens from {sorted(LENSES)}.")
        plausible = finding["verdict"] == "plausible"
        if plausible and finding["severity"] == "blocking":
            raise ValueError(f"Issue {index} cannot be both plausible and blocking.")
        prefix = "question:" if plausible else ("issue (blocking):" if finding["severity"] == "blocking" else "suggestion:")
        if not finding["comment"].startswith(prefix):
            raise ValueError(f"Issue {index} comment must start with {prefix!r}.")
        quotes = [part for match in re.findall(r'"([^"\n]+)"|`([^`\n]+)`|“([^”\n]+)”', finding["failure_scenario"]) for part in match if part]
        if not any(anchor and any(quote in anchor and len(quote) >= min(20, len(anchor)) for quote in quotes) for anchor in anchors(context, finding)):
            raise ValueError(f"Issue {index} needs an exact source quote at its file:line in failure_scenario.")

    notes_path = directory / "reviewed-notes.json"
    notes = json.loads(notes_path.read_text()) if notes_path.exists() else None
    if notes is not None and not isinstance(notes, list):
        raise ValueError("reviewed-notes.json must be an array.")
    for index, note in enumerate(notes or [], 1):
        check_shape(note, f"Design note {index}", NOTE_FIELDS)
        if note["lens"] not in NOTE_LENSES or note["second_opinion"] not in OPINION:
            raise ValueError(f"Design note {index} needs a lens from {sorted(NOTE_LENSES)} and a surviving second_opinion.")
        if not note["comment"].startswith(NOTE_PREFIX):
            raise ValueError(f"Design note {index} comment must start with {NOTE_PREFIX!r}.")
        if not any(anchors(context, note)):
            raise ValueError(f"Design note {index} needs a nonblank source line at its file:line.")

    findings = merge(findings, lambda issue: (issue["file"], issue["claim"]),
                     lambda issue: (SEVERITY[issue["severity"]], VERDICT[issue["verdict"]], -len(issue["found_by"]), issue["file"], issue["line"]))
    omitted = max(0, len(findings) - 10)
    findings = findings[:10]
    sections = [f"## Summary\n\n{summary}", "## Issues"]
    for index, finding in enumerate(findings, 1):
        sections.append(render(f"{index}. {finding['file']}:{finding['line']}", finding, ("file", "line", "severity", "lens", "claim", "failure_scenario", "verdict")))
    if not findings:
        sections.append("No supported issues found.")
    if omitted:
        sections.append(f"{omitted} additional issues omitted by the ten-issue cap.")

    if notes is not None:
        notes = merge(notes, lambda note: (note["file"], note["note"]),
                      lambda note: (OPINION[note["second_opinion"]], -len(note["found_by"]), note["file"], note["line"]))
        omitted_notes = max(0, len(notes) - 5)
        notes = notes[:5]
        sections.append("## Design notes\n\nOpinions, not verified defects. A second model agreed with each one, fully or in part.")
        for index, note in enumerate(notes, 1):
            sections.append(render(f"Note {index}. {note['file']}:{note['line']}", note, ("file", "line", "lens", "note", "second_opinion")))
        if not notes:
            sections.append("No design notes.")
        if omitted_notes:
            sections.append(f"{omitted_notes} additional design notes omitted by the five-note cap.")
        (directory / "notes.json").write_text(json.dumps(notes, indent=2) + "\n")

    report = "\n\n".join(sections) + "\n"
    (directory / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    (directory / "review.md").write_text(report)
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: finish_review.py ARTIFACT_DIRECTORY")
    try:
        print(finish(sys.argv[1]), end="")
    except (ValueError, OSError, KeyError) as error:
        sys.exit(f"code-turtle: {error}")
