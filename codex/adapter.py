#!/usr/bin/env python3
"""Lightkeeper's Codex adapter. Codex runs it from codex/hooks.json, once per
hook event: `python3 adapter.py <hook>` with Codex's JSON payload on stdin.
It drives lib/hooks/run.py through the same stdin/stdout contract Claude Code
uses, and changes only what Codex's hook contract does differently:

  * PreToolUse: Codex edits files with apply_patch, whose tool_input is the
    patch text. Every file the patch adds, updates, deletes or moves to gets
    the pointer an Edit of that file would get, before the patch lands.
  * Stop: Codex's Stop output has no additionalContext. The reminder the
    agent should act on goes back as {"decision": "block", "reason": ...},
    which Codex feeds to the agent as its next prompt. The reminder itself
    is sent at most once per session and never while stop_hook_active is
    set, so it can't loop; the user sees the same text as a systemMessage.
  * SessionStart and UserPromptSubmit: unchanged.

Prints at most one JSON object and always exits 0. Python 3.9, stdlib only.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RUN = str(Path(__file__).resolve().parent.parent / "lib" / "hooks" / "run.py")
PATCH_PATH = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+?)\s*$", re.M)
MAX_FILES = 6


def hook(name, payload):
    """One Lightkeeper hook's JSON object, or {} when it is silent or fails."""
    try:
        r = subprocess.run([sys.executable, RUN, name], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=9,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": payload.get("cwd") or os.getcwd()})
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except Exception:
        return {}


def patch_paths(payload):
    """The files an apply_patch call touches, absolute, in patch order."""
    patch = (payload.get("tool_input") or {}).get("command")
    if not isinstance(patch, str):
        return []
    cwd = payload.get("cwd") or os.getcwd()
    out = []
    for p in PATCH_PATH.findall(patch):
        p = os.path.normpath(os.path.join(cwd, p))
        if p not in out:
            out.append(p)
    return out[:MAX_FILES]


def translate(name, payload):
    if name == "file_guard":
        texts = []
        for path in patch_paths(payload):
            out = hook(name, dict(payload, tool_input={"file_path": path}))
            text = (out.get("hookSpecificOutput") or {}).get("additionalContext")
            if text:
                texts.append(text)
        if not texts:
            return {}
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "additionalContext": "\n".join(texts)}}
    out = hook(name, payload)
    if name == "stop_reminder":
        res = {}
        if out.get("systemMessage"):
            res["systemMessage"] = out["systemMessage"]
        ctx = (out.get("hookSpecificOutput") or {}).get("additionalContext")
        if ctx:
            res.update({"decision": "block", "reason": ctx})
        return res
    return out


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        payload = payload if isinstance(payload, dict) else {}
    except Exception:
        payload = {}
    try:
        res = translate(name, payload)
    except Exception:
        res = {}
    if res:
        print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
    sys.exit(0)
