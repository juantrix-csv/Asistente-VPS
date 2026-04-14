---
name: obsidian-vault
description: Use this skill when the user asks to save, search, connect, summarize, or update notes in the Obsidian vault through OpenClaw memory-wiki.
---

# Obsidian Vault

You are connected to a Markdown vault that the user opens with Obsidian.

## Operating Rules

- Prefer the memory-wiki tools for reading and writing notes.
- Search before creating a new note when the topic may already exist.
- Keep notes in plain Markdown that renders well in Obsidian.
- Use `[[wikilinks]]` for durable cross-references when a related note exists or should exist.
- Do not overwrite human-authored content without first checking the existing note.
- If the request is ambiguous, create or append under an inbox/daily note instead of inventing a permanent structure.
- When saving something from Telegram, include enough context to understand why it was saved later.

## Suggested Note Shape

Use this shape for new durable notes:

```markdown
# Title

## Summary

Short summary in the user's language.

## Details

- Key fact or decision.
- Relevant source, chat, or date when useful.

## Links

- [[Related Note]]
```

## Daily Capture

Use daily capture for quick messages, reminders, or rough thoughts:

```markdown
## HH:mm - Telegram

Content from the user.
```
