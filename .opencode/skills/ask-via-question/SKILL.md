---
name: ask-via-question
description: Force the agent to use OpenCode's question tool whenever it needs clarification, missing requirements, user preferences, approval on ambiguous choices, or any other direct user input.
---

# Ask Via Question

Use this skill whenever the task is incomplete, ambiguous, preference-sensitive, or requires confirmation from the user.

## Core rule

If you need to ask the user anything, you must use the OpenCode `question` tool.

Do not ask the user for clarification in normal assistant prose when the `question` tool is available.
Do not mix freeform chat questions with a `question` tool prompt for the same decision.
Do not guess when user input is required to proceed safely or correctly.

## When to use the question tool

Use the `question` tool whenever you need:
- Missing requirements
- User preferences
- Clarification of ambiguous instructions
- A decision between multiple implementation choices
- Confirmation before taking a risky or irreversible path
- Naming, styling, architecture, or product-direction choices that the codebase cannot answer confidently

## How to ask

When calling the `question` tool:
1. Write a short header.
2. Ask one clear question.
3. Provide 2-5 concrete options when possible.
4. Allow the user to type a custom answer if none of the options fit.
5. If there are multiple unknowns, batch related questions together instead of asking them one at a time.

## Decision policy

- If the repository, existing code, or prior user messages already answer the question, do not ask.
- If the choice is trivial and low-risk, proceed without asking.
- If the choice materially affects output, behavior, UX, architecture, or file structure, ask first.
- If blocked by missing information, ask before continuing.

## Examples

### Good
- Ask which framework the user wants before scaffolding a new app.
- Ask whether to optimize for speed or readability before refactoring a critical module.
- Ask which authentication provider to integrate when none is specified.

### Bad
- Asking in plain chat: "Which option do you want?"
- Guessing a database or framework when the user did not specify one.
- Asking unnecessary questions that can be answered from the codebase.

## Fallback

If the `question` tool is unavailable or denied by permissions, state that you are blocked because this skill requires the `question` tool for user-facing questions, then ask the user to enable it.