#!/usr/bin/env python3
"""Hook entry point: `python3 run.py <hook>`.

Reads the hook payload from stdin, finds the vault that covers the project
(CLAUDE_PROJECT_DIR, then the payload's cwd), loads its config and runs the
named hook's run(payload). Silent no-op when no vault covers the project, when
the vault is unusable, or on any error. Always exits 0 and never prints
anything except the hook's own single JSON object.

Each run is also counted in the session state (runs, and runs that told the
agent something), which `vault status --session` reads back.
"""
import contextlib
import importlib
import io
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

HOOKS = {"session_start", "prompt_hint", "file_guard", "stop_reminder"}


def record(hook, payload, said):
    session = payload.get("session_id")
    if not session:
        return
    import _util
    if hook == "file_guard":
        hook = "read_pointer" if _util.is_read(payload) else "edit_pointer"
    state = _util.load_state(session)
    now = time.time()
    state.setdefault("started", now)
    state["last"] = now
    for key, counted in (("runs", True), ("said", said)):
        if counted:
            counts = state.setdefault(key, {})
            counts[hook] = counts.get(hook, 0) + 1
    if hook == "session_start" and payload.get("source") == "compact":
        state["compactions"] = state.get("compactions", 0) + 1
    _util.save_state(session, state)


def main():
    hook = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    try:
        payload = json.loads(raw or "{}")
        payload = payload if isinstance(payload, dict) else {}
    except ValueError:
        payload = {}
    if hook not in HOOKS:
        return
    try:
        import vaultlib
        cwd = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
        if not vaultlib.init(cwd=cwd):
            return
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            importlib.import_module(hook).run(payload)
        sys.stdout.write(out.getvalue())
        sys.stdout.flush()
        record(hook, payload, bool(out.getvalue().strip()))
    except Exception:
        if os.environ.get("VAULT_HOOK_DEBUG"):
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
    sys.exit(0)
