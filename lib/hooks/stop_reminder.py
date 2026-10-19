#!/usr/bin/env python3
"""Stop hook: nudge when watched code moved this session but the knowledge
vault didn't, naming the EXACT notes the changed files belong to.

Quiet when: nothing watched moved / the vault is already dirty / the vault
was committed within the window / stop_hook_active. Advisory only.

Once per session (and only when VAULT_STOP_NUDGE != quiet) the same
information is also delivered as additionalContext so the agent can act on
it: update the notes now, or say why no update is needed. The vault-moved
quiet check is the natural loop breaker.

Config: the matched repo's `watched` list and `stop_window_hours` from
vault.json. Env overrides: VAULT_WATCHED (space-separated),
VAULT_WINDOW_HOURS, VAULT_STOP_NUDGE=quiet."""
import json
import os
import subprocess

import _util
import vaultlib

DEFAULT_WATCHED = "src app lib"
MAX_NAMED_NOTES = 6


def git(args, cwd=None):
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True,
                           timeout=8, cwd=cwd)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def changed_files(repo, watched, since):
    files = set()
    # working tree + index (NUL-parsed so spaces survive; R/C carry an extra field).
    # -uall lists files inside NEW directories one by one; the default collapses
    # them to "src/NewThing/", which then maps to no note.
    out = git(["status", "--porcelain", "-z", "-uall", "--"] + watched, cwd=repo)
    if out:
        records = out.split("\0")
        i = 0
        while i < len(records):
            rec = records[i]
            i += 1
            if len(rec) < 4:
                continue
            status, path = rec[:2], rec[3:]
            files.add(path)
            if status[0] in ("R", "C"):
                i += 1  # skip the origin path record
    out = git(["log", "--since", since, "--name-only", "-z",
               "--pretty=format:", "--"] + watched, cwd=repo)
    if out:
        for rec in out.split("\0"):
            rec = rec.strip("\n")
            if rec:
                files.add(rec)
    return sorted(files)


def run(payload):
    if payload.get("stop_hook_active"):
        return
    vault = str(vaultlib.VAULT_ROOT)
    cfg = vaultlib.CONFIG
    hours = os.environ.get("VAULT_WINDOW_HOURS") or str(cfg.get("stop_window_hours") or 6)
    entry = vaultlib.MATCHED_REPO[1] if vaultlib.MATCHED_REPO else {}
    watched = (os.environ.get("VAULT_WATCHED")
               or " ".join(entry.get("watched") or [])
               or DEFAULT_WATCHED).split()
    since = "%s hours ago" % hours

    cwd = payload.get("cwd") or os.getcwd()
    repo = (git(["rev-parse", "--show-toplevel"], cwd=cwd) or "").strip()
    if not repo or not os.path.isdir(os.path.join(vault, ".git")):
        return
    sub = entry.get("root")
    if sub:
        watched = [os.path.join(sub.strip("/"), w) for w in watched]

    touched = changed_files(repo, watched, since)
    if not touched:
        return

    # did the vault move? (dirty or committed within the window -> assume handled)
    # .obsidian/ is excluded from both: the editor rewrites its own config on every
    # graph pan or zoom, and neither that nor committing it means a note changed.
    notes = ["--", ".", ":(exclude).obsidian"]
    dirty = git(["status", "--porcelain"] + notes, cwd=vault)
    recent = git(["log", "--since", since, "--oneline", "-1"] + notes, cwd=vault)
    if (dirty or "").strip() or (recent or "").strip():
        return

    stems, unmatched = [], 0
    try:
        idx = _util.get_index()
        for f in touched:
            owners = [s for s, _via, prio in vaultlib.match_paths(idx, [f])
                      if prio < 3]
            if owners:
                for s in owners[:2]:
                    if s not in stems:
                        stems.append(s)
            else:
                unmatched += 1
    except Exception:
        unmatched = len(touched)

    named = ", ".join(stems[:MAX_NAMED_NOTES])
    if len(stems) > MAX_NAMED_NOTES:
        named += " (+%d more)" % (len(stems) - MAX_NAMED_NOTES)

    parts = ["Knowledge vault not updated. %d file(s) under %s changed in the "
             "last %sh, but no note in the vault moved."
             % (len(touched), ", ".join(watched), hours)]
    if named:
        parts.append("Affected notes: %s." % named)
    if unmatched:
        parts.append("%d changed file(s) match no note — a new module or an "
                     "undocumented surface?" % unmatched)
    parts.append("Update the note(s): amend 'How it works' / 'Gotchas', bump "
                 "'updated:' (knowledge-vault skill). Vault: %s" % vault)
    msg = " ".join(parts)

    out = {"systemMessage": msg}
    if os.environ.get("VAULT_STOP_NUDGE", "").lower() != "quiet":
        session = payload.get("session_id", "unknown")
        state = _util.load_state(session)
        if not state.get("stop_ctx_sent"):
            state["stop_ctx_sent"] = True
            _util.save_state(session, state)
            out["hookSpecificOutput"] = {
                "hookEventName": "Stop",
                "additionalContext": (
                    msg + "\nAct on this now: read the named note(s) and update "
                    "what this session changed — or state briefly why no vault "
                    "update is needed."),
            }
    print(json.dumps(out, ensure_ascii=False))
