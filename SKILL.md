---
name: capy-session
description: >
  Manage HappyCapy sessions and desktops using the capy-cli tool. Use this skill
  whenever the user wants to list, create, rename, or delete HappyCapy sessions or
  desktops — including phrasing like "show my sessions", "create a new session",
  "list desktops", "rename this session", "delete session", "manage my capy sessions",
  or "set up capy-cli auth". Also trigger when the user asks about HappyCapy session
  management, wants to organize their AI workspaces, or mentions session IDs or
  desktop IDs in a HappyCapy context.
---

# capy-session — HappyCapy Session Manager

This skill lets you manage HappyCapy sessions and desktops via the `capy-cli` tool.
The CLI script is bundled at `scripts/capy-cli.py` in this skill directory.

## Setup

Before any session operations, ensure `capy-cli` is installed and configured.

### Install dependencies

```bash
pip install requests -q
```

### Set up the CLI alias (one-time)

```bash
# Copy to a convenient location if not already there
SKILL_DIR="$(dirname "$0")"
CAPY_CLI="python $SKILL_DIR/scripts/capy-cli.py"
```

Or reference the script directly via its full path:
```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py <command>
```

### Configure authentication

The CLI needs a Bearer token and session cookies from happycapy.ai.

```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py \
  config --token TOKEN --cookies "COOKIE_STRING"
```

If the user hasn't configured this yet, ask them to:
1. Open happycapy.ai in their browser
2. Open DevTools → Network tab
3. Make any request and copy the `Authorization: Bearer <token>` value
4. Copy the full `Cookie:` header value
5. Run the config command above

Check current config (masked display):
```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py config
```

## Commands Reference

### List desktops

```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py desktops [--limit 50] [--offset 0]
```

Shows: ID, Title, Model, Updated timestamp for each desktop.

### List sessions in a desktop

```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py sessions DESKTOP_ID
```

Shows: ID, Title, Model, Updated timestamp for all sub-sessions.

### Create a new session

```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py create DESKTOP_ID "Session Title" [--model MODEL]
```

Default model: `claude-sonnet-4-6`. Other options: `claude-opus-4-6`, `claude-haiku-4-5`.

### Rename a session

```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py rename SESSION_ID "New Title"
```

### Delete a session

```bash
python /home/node/.claude/skills/capy-session/scripts/capy-cli.py delete SESSION_ID [--force]
```

Without `--force`, the CLI prompts for confirmation. In automated/scripted contexts, use `--force` and confirm with the user beforehand.

## Default Desktop

The current desktop ID can be extracted from `pwd`. The workspace path contains the desktop UUID as a segment, for example:

```
/home/node/a0/workspace/bcd8b15b-de4c-443c-9d83-afc82fa10f39/workspace
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                         this segment is the desktop ID
```

Extract it with:
```bash
pwd | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1
```

### When to use the default desktop

| Situation | Behavior |
|-----------|----------|
| User says "当前桌面" / "current desktop" | Extract ID from pwd, use directly, **no confirmation needed** |
| No desktop specified by user | Extract ID from pwd, **ask user to confirm** before proceeding |
| User provides an explicit desktop ID | Use that ID directly |

Example confirmation message when defaulting:
> 我将使用当前桌面（ID: `bcd8b15b-de4c-443c-9d83-afc82fa10f39`），确认继续吗？

## Workflow Guidelines

### When the user's intent is clear

Run the relevant command directly and present the output in a readable way. For listing operations, you can format the table output or summarize key info. For create/rename/delete, confirm what was done and show the result.

### When the user needs to find a session first

If the user says something like "delete my 'Research' session" but doesn't have the ID:
1. Determine the desktop (default desktop or ask)
2. Run `sessions DESKTOP_ID` to list sessions
3. Find the matching session and confirm with the user before acting

### Session index references

Users may refer to sessions by position (e.g., "第6到8个会话", "sessions 6~8"). In this case:
1. Run `sessions DESKTOP_ID` to get the full list
2. Pick sessions at positions 6–8 (1-indexed, ordered as returned by the API)
3. Show the user which sessions those are and confirm before any destructive action

### Deletion safety

Always confirm with the user before deleting, unless they've explicitly said "force delete" or "without asking". Even when using `--force` in the command, make sure you've asked the user first in the conversation.

### Error handling

If you get a `401 Unauthorized` error, the token or cookies may have expired. Guide the user to:
1. Re-fetch credentials from DevTools
2. Re-run the `config` command

If you get a `404`, the session or desktop ID may be wrong — double-check with the user.

## Example Interactions

**User**: "Show me all my desktops"
→ Run `desktops`, present the list clearly.

**User**: "Create a session called 'Data Analysis' in my main desktop"
→ Run `desktops` to find the main desktop, then `create DESKTOP_ID "Data Analysis"`.

**User**: "List all sessions in desktop abc-123"
→ Run `sessions abc-123`, show the results.

**User**: "Rename session xyz-789 to 'Q1 Planning'"
→ Run `rename xyz-789 "Q1 Planning"`, confirm success.

**User**: "Delete all sessions older than last week"
→ List sessions, show the user which ones qualify, ask for confirmation, then delete one by one.

**User**: "帮我清理当前桌面的第6~8个会话"
→ Extract desktop ID from pwd, run `sessions DESKTOP_ID`, pick sessions at index 6–8, show the user their titles, confirm, then delete each with `--force`.

**User**: "列出会话" (no desktop specified)
→ Extract desktop ID from pwd, confirm: "我将使用当前桌面（`<ID>`），确认继续吗？", then run `sessions DESKTOP_ID`.
