#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def run(*args, cwd=None, data=None):
    result = subprocess.run(args, cwd=cwd, input=data, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def prepare(target):
    repo = Path(run("git", "rev-parse", "--show-toplevel").decode().strip())

    def git(*args, data=None):
        return run("git", *args, cwd=repo, data=data)

    def revision(ref):
        return git("rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()

    def exists(ref):
        return subprocess.run(
            ["git", "rev-parse", "--verify", "--end-of-options", ref + "^{commit}"],
            cwd=repo, capture_output=True,
        ).returncode == 0

    def branch_ref(ref):
        return next((name for name in ("refs/heads/" + ref, "refs/remotes/" + ref) if exists(name)), None)

    def scoped_path(value):
        path = Path(os.path.abspath(repo / value))
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError:
            raise ValueError("The path must be inside the target repository.") from None
        literal = ":(literal)" + relative
        if not git("ls-files", "--with-tree=HEAD", "-z", "--", literal):
            raise ValueError("The path has no tracked files; untracked files are excluded.")
        return relative, literal

    scope = None
    pathspec = []
    head = None
    base = revision("HEAD")
    kind, value = (target.split(":", 1) if target.startswith(("path:", "branch:", "commit:")) else (None, target))
    if not target:
        pass
    elif kind == "path":
        scope, literal = scoped_path(value)
        pathspec = [literal]
    elif re.fullmatch(r"#?[0-9]+", value) and kind is None:
        if not value.startswith("#") and exists(value):
            raise ValueError("Target is both a PR number and a commit. Use #N for the PR or commit: for the commit.")
        pr = json.loads(run("gh", "pr", "view", value.lstrip("#"), "--json", "baseRefOid,headRefOid", cwd=repo))
        if not all(exists(pr[key]) for key in ("baseRefOid", "headRefOid")):
            raise ValueError("PR objects are missing locally. Fetch the PR base and head, then retry; no fetch was performed.")
        head = revision(pr["headRefOid"])
        base = git("merge-base", revision(pr["baseRefOid"]), head).decode().strip()
    elif ".." in value and kind is None:
        separator = "..." if "..." in value else ".."
        parts = value.split(separator)
        is_range = len(parts) == 2 and all(parts) and all(exists(part) for part in parts)
        tracked = git("ls-files", "--with-tree=HEAD", "-z", "--", ":(literal)" + value)
        if is_range and tracked:
            raise ValueError("Target is both a tracked path and a range. Use path: for the path.")
        if is_range:
            base, head = (revision(part) for part in parts)
            if separator == "...":
                base = git("merge-base", base, head).decode().strip()
        elif tracked:
            scope, literal = scoped_path(value)
            pathspec = [literal]
        else:
            raise ValueError("Use a complete base..head or base...head range of existing commits.")
    else:
        ref = branch_ref(value) if kind != "commit" else None
        tracked = git("ls-files", "--with-tree=HEAD", "-z", "--", ":(literal)" + value)
        if kind is None and tracked and (ref or exists(value)):
            raise ValueError("Target is both a tracked path and a ref. Use path:, branch:, or commit:.")
        if ref or kind == "branch":
            if not ref:
                raise ValueError("The requested local or remote branch does not exist.")
            default = next((name for name in ("refs/remotes/origin/HEAD", "refs/heads/main", "refs/heads/master") if exists(name)), None)
            if default is None:
                raise ValueError("No default branch found. Supply an explicit base...head range.")
            head = revision(ref)
            base = git("merge-base", revision(default), head).decode().strip()
        elif kind == "commit" or exists(value):
            head = revision(value)
            parents = git("rev-list", "--parents", "-n", "1", head).decode().split()[1:]
            base = parents[0] if parents else None
        else:
            scope, literal = scoped_path(value)
            pathspec = [literal]

    diff_args = ["diff", base] if head is None else (["diff", base, head] if base else ["diff-tree", "--root", "--no-commit-id", "-r", head])
    flags = ["--no-ext-diff", "--no-textconv", "--no-renames"]
    diff = git(*diff_args, *flags, "--binary", "--full-index", "--", *pathspec)
    stats = git(*diff_args, *flags, "--numstat", "-z", "--", *pathspec)
    changed_lines = 0
    binary_files = []
    changed_paths = set()
    for record in stats.split(b"\0"):
        if record:
            added, deleted, name = record.split(b"\t", 2)
            changed_paths.add(os.fsdecode(name))
            if added == b"-":
                binary_files.append(os.fsdecode(name))
            else:
                changed_lines += int(added) + int(deleted)

    temporary_root = Path(tempfile.gettempdir()).resolve()
    if temporary_root.is_relative_to(repo):
        raise ValueError("The temporary directory is inside the repository. Set TMPDIR outside the checkout and retry.")
    artifacts = Path(tempfile.mkdtemp(prefix="code-turtle-", dir=temporary_root))
    before = artifacts / "before"
    after = artifacts / "after"
    before.mkdir()
    after.mkdir()
    unavailable = set()

    def save(destination, name, content):
        path = destination / os.fsdecode(name)
        if not path.is_relative_to(destination) or ".." in path.parts:
            raise ValueError("Unsafe source path in Git tree.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def snapshot(ref, destination):
        if ref is None:
            return
        entries = [record.split(b"\t", 1) for record in git("ls-tree", "-r", "-z", ref).split(b"\0") if record]
        blobs = []
        for metadata, name in entries:
            mode, object_type, oid = metadata.split()
            if object_type == b"blob":
                blobs.append((oid, name))
            else:
                unavailable.add(os.fsdecode(name))
        payload = git("cat-file", "--batch", data=b"".join(oid + b"\n" for oid, _ in blobs))
        offset = 0
        for oid, name in blobs:
            boundary = payload.index(b"\n", offset)
            actual_oid, object_type, size = payload[offset:boundary].split()
            if actual_oid != oid or object_type != b"blob":
                raise ValueError("Git returned an unexpected snapshot object.")
            offset = boundary + 1
            length = int(size)
            save(destination, name, payload[offset:offset + length])
            offset += length + 1

    snapshot(base, before)
    if head:
        snapshot(head, after)
    else:
        for name in set(git("ls-files", "--cached", "-z").split(b"\0")) - {b""}:
            source = repo / os.fsdecode(name)
            if source.is_symlink():
                save(after, name, os.fsencode(os.readlink(source)))
            elif source.is_file():
                save(after, name, source.read_bytes())
            elif source.is_dir():
                unavailable.add(os.fsdecode(name))

    unavailable &= changed_paths
    (artifacts / "diff.patch").write_bytes(diff)
    context = {
        "repo_root": str(repo), "target": target or "tracked working copy", "scope": scope,
        "diff_range": f"{base or 'empty tree'}..{head or 'working copy'}",
        "diff_path": str(artifacts / "diff.patch"), "before_root": str(before), "after_root": str(after),
        "schema_path": str(Path(__file__).resolve().parents[1] / "references" / "finding-schema.md"),
        "lenses_path": str(Path(__file__).resolve().parents[1] / "references" / "lenses.md"),
        "changed_files": sorted(changed_paths), "changed_lines": changed_lines, "binary_files": binary_files, "unavailable_submodules": sorted(unavailable),
        "mode": "small" if changed_lines < 50 and not binary_files and not unavailable else "full",
        "empty": not diff,
    }
    (artifacts / "context.json").write_text(json.dumps(context, indent=2) + "\n")
    return context


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit("Usage: prepare_review.py [PR# | branch | commit | base..head | path]")
    try:
        print(json.dumps(prepare(sys.argv[1] if len(sys.argv) == 2 else ""), indent=2))
    except (ValueError, OSError) as error:
        sys.exit(f"code-turtle: {error}")
