#!/usr/bin/env python3
"""Shared plumbing for the vault's Claude Code hooks.

Contract for every hook in this directory:
  * read nothing from stdin yourself (run.py hands you the payload),
  * NEVER raise out of run(), NEVER write to stdout except one JSON object
    (a stray non-zero exit from a UserPromptSubmit hook would ERASE the
    user's prompt; malformed stdout shows up as a hook error),
  * stay quiet when there is nothing worth saying.
Python 3.9, stdlib only.
"""
import glob
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vaultlib  # noqa: E402

STATE_TTL = 24 * 3600
PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def read_payload():
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _state_dir():
    return os.environ.get("TMPDIR") or "/tmp"


def state_path(session_id):
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:80]
    return os.path.join(_state_dir(), vaultlib.STATE_PREFIX + (safe or "unknown") + ".json")


def load_state(session_id):
    try:
        with open(state_path(session_id)) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(session_id, state):
    try:
        with open(state_path(session_id), "w") as f:
            json.dump(state, f)
    except OSError:
        return
    # opportunistic GC of stale sibling session states
    try:
        cutoff = time.time() - STATE_TTL
        for p in glob.glob(os.path.join(_state_dir(), vaultlib.STATE_PREFIX + "*.json")):
            try:
                if os.path.getmtime(p) < cutoff and not p.endswith("-vault.json"):
                    os.unlink(p)
            except OSError:
                pass
    except Exception:
        pass


def vault_state():
    """Per-vault (not per-session) scratch state, e.g. when a nudge was last shown."""
    return load_state("vault")


def save_vault_state(state):
    save_state("vault", state)


def emit_context(event, text):
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": text}
    }, ensure_ascii=False))


def get_index():
    return vaultlib.load_index()


def cli(sub):
    """How to invoke a vault subcommand from a shell: the installed launcher
    when present, otherwise the plugin's own script."""
    if shutil.which("vault"):
        return "vault " + sub
    name = {"find": "find.py", "check": "check.py", "sync": "sync.py", "status": "status.py"}.get(sub.split()[0])
    if name:
        return ("python3 %s %s" % (PLUGIN_ROOT / "lib" / name, " ".join(sub.split()[1:]))).rstrip()
    return "vault " + sub
