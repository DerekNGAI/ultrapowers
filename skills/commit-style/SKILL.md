---
name: commit-style
description: Atomic commits with Conventional Commits messages. Use when creating a git commit, writing or rewording a commit message, or splitting changes into commits.
---

# Commit style

This skill governs how to commit. Whether to commit stays with the user's or the brief's authorization.

## Steps

1. **Read the convention.** Run `git log --oneline -20`, and read any commitlint config (`commitlint.config.*`, `.commitlintrc*`, `package.json`) and `CONTRIBUTING.md`. The repository's types, scopes, length limits, language, and trailers override the defaults below. Done when you can name the scopes in use and every enforced limit.
2. **Plan atomic commits.** Read `git status` and the full diff, staged and unstaged. An *atomic* commit is one logical change that builds and passes its tests alone and can be reverted alone. Split when the header needs "and" or the change fits two types: a refactor that enables a fix is two commits, refactor first. Give formatting-only and rename-only changes their own commits so behavioural diffs stay readable. Done when every changed hunk belongs to exactly one planned commit or is deliberately left uncommitted.
3. **Stage by path.** Run `git add <path>...` for one planned commit, then read `git diff --cached` and confirm it holds that commit and nothing else. When one file carries hunks for two commits, stage the hunk with `git apply --cached <patch>`. Secrets, `.env` files, build output, and changes you did not make stay unstaged.
4. **Verify.** Run the project's checks that cover the staged change. Hooks run on every commit; a failing hook is a finding to fix before committing again.
5. **Write the message** per [Message](#message).
6. **Commit and confirm.** Pass the message through a file or heredoc (`git commit -F -`) so the body keeps its blank lines and wrapping. Then run `git log -1 --format=%B` and `git status`. Done when the message reads as written and the tree matches the plan. Repeat steps 3 to 6 for each planned commit.

## Message

```
<type>[(<scope>)][!]: <description>

[body]

[footers]
```

### Header

| Type | Use when the commit | Release |
| --- | --- | --- |
| `feat` | adds a capability users of the code can reach | minor |
| `fix` | corrects wrong behaviour | patch |
| `perf` | keeps behaviour and makes it faster or lighter | |
| `refactor` | restructures code and keeps behaviour | |
| `docs` | changes documentation only | |
| `test` | adds or corrects tests only | |
| `style` | changes formatting only | |
| `build` | changes the build system or dependencies | |
| `ci` | changes CI configuration | |
| `chore` | does maintenance that fits no type above | |
| `revert` | reverts an earlier commit | |

Release tools derive the version bump and changelog from the type, so choose it by the change's effect on users of the code.

- **Scope.** A noun for the area changed, reused from the log. Omit it when the change spans areas.
- **Description.** Imperative mood, completing "If applied, this commit will …". Lowercase first word, no closing period. Name the behaviour that changed: `fix(auth): reject expired refresh tokens` tells the reader more than `fix: auth bug`.
- **Length.** Aim for a 50-character header. 72 is the limit.

### Body

Add a body when the header alone leaves the reason unclear. Explain why the change was needed and what behaves differently now; the diff already shows how. Record what the diff cannot: the constraint, the rejected alternative, the side effect. Separate it from the header with one blank line and wrap at 72 columns.

### Footers

Git trailers, one per line, after one blank line:

- `BREAKING CHANGE: <what breaks and how to migrate>`
- `Refs: #123` for a related issue, `Closes #123` to close one on merge
- `Co-authored-by: Name <email>`, plus any attribution trailer the harness or repository requires

### Breaking changes

Put `!` before the colon and add a `BREAKING CHANGE:` footer. Either one triggers a major release; the `!` makes the break visible in `git log --oneline`, and the footer carries the migration.

### Reverts

Run `git revert <sha>`, then give the commit the header `revert: <reverted header>`, the reason in the body, and a `Refs: <sha>` footer.

## History

- Correct your own unpushed commit with `git commit --amend` or `git commit --fixup <sha>`. Correct a pushed commit with a new commit, so shared history stays append-only.
- Where the repository squash-merges, the PR title becomes the commit header. Write it to the header rules.

## Examples

```
feat(orca-poteto): clean up worktrees after a run
```

```
fix(parser): keep trailing newline in heredocs

The lexer trimmed every token, so a heredoc lost its final newline
and scripts that piped it to `wc -l` counted one line short. Trim
only non-heredoc tokens.

Closes #482
```

```
feat(api)!: use ISO 8601 timestamps in /events

Clients in other time zones misread the epoch-seconds field as local
time. ISO 8601 with an explicit offset removes the ambiguity.

BREAKING CHANGE: `created_at` is now a string such as
`2026-11-11T09:30:00Z`. Parse it as a date instead of a number.
```
