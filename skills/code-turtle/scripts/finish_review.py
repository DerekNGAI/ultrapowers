#!/usr/bin/env python3
import json
from pathlib import Path, PurePosixPath
import re
import sys


FIELDS = {"file", "line", "severity", "claim", "failure_scenario", "comment", "verdict", "found_by"}
TEXT_FIELDS = FIELDS - {"line", "found_by"}
SEVERITY = {"blocking": 0, "should-fix": 1, "minor": 2}
VERDICT = {"confirmed": 0, "plausible": 1}


def finish(artifact_directory):
    directory = Path(artifact_directory).resolve()
    context = json.loads((directory / "context.json").read_text())
    repo = Path(context["repo_root"]).resolve()
    for name in ("findings.json", "review.md"):
        if (directory / name).resolve().is_relative_to(repo):
            raise ValueError("Review output must be outside the repository.")
    summary = (directory / "summary.md").read_text().strip()
    if not summary:
        raise ValueError("summary.md must contain the plain-language summary.")
    findings = json.loads((directory / "reviewed-findings.json").read_text())
    if not isinstance(findings, list):
        raise ValueError("reviewed-findings.json must be an array.")
    for index, finding in enumerate(findings, 1):
        if not isinstance(finding, dict) or set(finding) != FIELDS:
            raise ValueError(f"Issue {index} must have exactly {sorted(FIELDS)}.")
        if type(finding["line"]) is not int or finding["line"] < 1:
            raise ValueError(f"Issue {index} needs a positive integer line.")
        if any(not isinstance(finding[key], str) or not finding[key].strip() for key in TEXT_FIELDS):
            raise ValueError(f"Issue {index} has an empty or non-string field.")
        found_by = finding["found_by"]
        if not isinstance(found_by, list) or not found_by or any(not isinstance(model, str) or not model.strip() for model in found_by) or len(set(found_by)) != len(found_by):
            raise ValueError(f"Issue {index} needs found_by as a nonempty list of distinct model labels.")
        path = PurePosixPath(finding["file"])
        if path.is_absolute() or ".." in path.parts or str(path) == ".":
            raise ValueError(f"Issue {index} needs a repository-relative file.")
        if finding["severity"] not in SEVERITY or finding["verdict"] not in VERDICT:
            raise ValueError(f"Issue {index} needs a supported severity and a surviving verdict.")
        plausible = finding["verdict"] == "plausible"
        if plausible and finding["severity"] == "blocking":
            raise ValueError(f"Issue {index} cannot be both plausible and blocking.")
        prefix = "question:" if plausible else ("issue (blocking):" if finding["severity"] == "blocking" else "suggestion:")
        if not finding["comment"].startswith(prefix):
            raise ValueError(f"Issue {index} comment must start with {prefix!r}.")
        quotes = [part for match in re.findall(r'"([^"\n]+)"|`([^`\n]+)`|“([^”\n]+)”', finding["failure_scenario"]) for part in match if part]
        quoted_anchor = False
        for key in ("before_root", "after_root"):
            source = Path(context[key]) / finding["file"]
            if source.is_file():
                lines = source.read_text(errors="replace").splitlines()
                if len(lines) >= finding["line"]:
                    anchor = lines[finding["line"] - 1].strip()
                    quoted_anchor |= bool(anchor) and any(quote in anchor and len(quote) >= min(20, len(anchor)) for quote in quotes)
        if not quoted_anchor:
            raise ValueError(f"Issue {index} needs an exact source quote at its file:line in failure_scenario.")

    findings.sort(key=lambda issue: (SEVERITY[issue["severity"]], VERDICT[issue["verdict"]], issue["file"], issue["line"]))
    unique = {}
    for finding in findings:
        kept = unique.setdefault((finding["file"], finding["claim"]), finding)
        kept["found_by"] = list(dict.fromkeys(kept["found_by"] + finding["found_by"]))
    findings = sorted(unique.values(), key=lambda issue: (SEVERITY[issue["severity"]], VERDICT[issue["verdict"]], -len(issue["found_by"]), issue["file"], issue["line"]))
    omitted = max(0, len(findings) - 10)
    findings = findings[:10]
    sections = [f"## Summary\n\n{summary}", "## Issues"]
    for index, finding in enumerate(findings, 1):
        fields = "\n".join(f"- **{key}:** {finding[key]}" for key in ("file", "line", "severity", "claim", "failure_scenario", "verdict"))
        fields += f"\n- **found_by:** {', '.join(finding['found_by'])}"
        fence = "`" * max(3, max((len(part) for part in re.findall(r"`+", finding["comment"])), default=0) + 1)
        sections.append(f"### {index}. {finding['file']}:{finding['line']}\n\n{fields}\n\n**comment:**\n\n{fence}\n{finding['comment']}\n{fence}")
    if not findings:
        sections.append("No supported issues found.")
    if omitted:
        sections.append(f"{omitted} additional issues omitted by the ten-issue cap.")
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
