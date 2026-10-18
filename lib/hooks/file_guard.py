#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit|MultiEdit|NotebookEdit): when the file about to
be edited is documented by a vault note the agent hasn't been pointed at this
session, inject the pointer BEFORE the edit lands. A stub note gets different
wording: there is nothing to read yet, so the ask is to write what you learn.

Emits only additionalContext, no permissionDecision, so it can never block
or alter the edit. Per-file resolution is cached in the session state so an
edit burst on the same file costs one small JSON read, no index load."""
import os

import _util
import vaultlib

MAX_NOTES = 2


def run(payload):
    tool_input = payload.get("tool_input") or {}
    fp = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not fp or not isinstance(fp, str):
        return
    if fp.startswith(str(vaultlib.VAULT_ROOT)):
        return  # never hint while editing the vault itself

    session = payload.get("session_id", "unknown")
    state = _util.load_state(session)
    seen = set(state.get("seen", []))
    file_cache = state.get("files", {})

    if fp in file_cache:
        stems = file_cache[fp]
        if not [s for s in stems if s not in seen]:
            return
        idx = _util.get_index()
        stems = [s for s in stems if s in idx["notes"]]
    else:
        idx = _util.get_index()
        matches = vaultlib.match_paths(
            idx, [fp],
            cwd=payload.get("cwd"),
            project_dir=os.environ.get("CLAUDE_PROJECT_DIR"),
        )
        # shared paths (priority 3, e.g. a global routes file) are too weak to hint on
        stems = [s for s, _via, prio in matches if prio < 3][:MAX_NOTES]
        file_cache[fp] = stems
        state["files"] = file_cache

    fresh = [s for s in stems if s not in seen]
    if not fresh:
        _util.save_state(session, state)
        return

    rel = fp
    for root in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd")):
        if root and fp.startswith(root.rstrip("/") + "/"):
            rel = fp[len(root.rstrip("/")) + 1:]
            break

    lines = []
    for stem in fresh:
        note = idx["notes"][stem]
        where = "%s/%s" % (vaultlib.VAULT_ROOT, note["path"])
        if note.get("depth") == "stub":
            lines.append(
                "`%s` belongs to vault note \"%s\", which is still a stub (nothing recorded "
                "yet): %s. If you learn how this area works or hit a trap, write it there "
                "and promote the note." % (rel, stem, where))
        else:
            lines.append(
                "`%s` is documented by vault note \"%s\" (updated %s) — read its Gotchas "
                "before going further: %s" % (rel, stem, note["updated"] or "?", where))
        nbrs = vaultlib.neighbors(idx, stem, 3)
        if nbrs:
            bits = []
            for d, other, reason in nbrs:
                r = (": " + vaultlib.trim(reason, 60)) if reason else ""
                bits.append("%s %s%s" % (d, other, r))
            lines.append("  connected — %s" % "; ".join(bits))
    lines.append("If this change alters behavior, updating the note afterwards "
                 "is part of the definition of done.")

    seen.update(fresh)
    state["seen"] = sorted(seen)
    _util.save_state(session, state)
    _util.emit_context("PreToolUse", "\n".join(lines))
