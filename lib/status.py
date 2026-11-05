#!/usr/bin/env python3
"""vault status: the vault on one screen.

    vault status            coverage, stale notes, attention signals, sync drift
    vault status --session  what the hooks did in the latest session: how often each
                            ran, the notes they surfaced, which of those were updated
    vault status --session=ID
    vault status --json
    vault status --vault PATH

Reads the index (rebuilt if notes changed), _meta/status.json (written by
`vault check --write`) and runs the sync report without fetching. --session
reads the per-session state the hooks keep under TMPDIR for 24 hours.
"""
import datetime
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402

HOOK_LABELS = (("session_start", "session primer"), ("prompt_hint", "prompt hints"),
               ("read_pointer", "read pointer"), ("edit_pointer", "edit pointer"),
               ("stop_reminder", "stop reminder"))


def vault_changes(root, since):
    """Vault paths that are uncommitted, or were committed after `since` (epoch)."""
    def git(args):
        try:
            r = subprocess.run(["git", "-C", str(root)] + args, capture_output=True, text=True, timeout=10)
            return r.stdout if r.returncode == 0 else ""
        except Exception:
            return ""
    paths = set()
    records = git(["status", "--porcelain", "-z", "-uall"]).split("\0")
    i = 0
    while i < len(records):
        rec = records[i]
        i += 1
        if len(rec) > 3:
            paths.add(rec[3:])
            if rec[0] in "RC":
                i += 1  # skip the origin path record
    if since:
        log = git(["log", "--since=@%d" % int(since), "--name-only", "--pretty=format:"])
        paths |= {p for p in log.splitlines() if p.strip()}
    return paths


def session_report(root, which, as_json):
    sdir = os.environ.get("TMPDIR") or "/tmp"
    prefix = os.path.join(sdir, vaultlib.STATE_PREFIX)
    files = [p for p in glob.glob(prefix + "*.json") if not p.endswith("-vault.json")]
    others = len(files) - 1
    if which:
        safe = "".join(c for c in which if c.isalnum() or c in "-_")[:80]
        files = [p for p in files if p == prefix + safe + ".json"]
    if not files:
        print("No session has run a Lightkeeper hook for this vault in the last 24 hours%s. "
              "Check that the plugin is enabled (/plugin in Claude Code) and that this checkout "
              "is covered (`vault status` from inside it)." % (" under that id" if which else ""))
        return 1
    path = max(files, key=os.path.getmtime)
    try:
        state = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        state = {}
    runs, said = state.get("runs") or {}, state.get("said") or {}
    surfaced = sorted(set(state.get("earlier") or []) | set(state.get("seen") or []))
    by_path = {n["path"]: s for s, n in vaultlib.load_index()["notes"].items()}
    changed = {by_path[p] for p in vault_changes(root, state.get("started")) if p in by_path}
    report = {
        "session": path[len(prefix):-len(".json")],
        "started": state.get("started"), "last": state.get("last"),
        "runs": runs, "said": said, "compactions": state.get("compactions", 0),
        "surfaced": surfaced,
        "updated": [s for s in surfaced if s in changed],
        "not_updated": [s for s in surfaced if s not in changed],
        "also_updated": sorted(changed - set(surfaced)),
    }
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    def when(ts):
        t = time.localtime(ts)
        same_day = time.strftime("%Y-%m-%d", t) == time.strftime("%Y-%m-%d")
        return time.strftime("%H:%M" if same_day else "%Y-%m-%d %H:%M", t)

    head = "Session %s" % report["session"]
    if report["started"] and report["last"]:
        head += " · hooks ran from %s to %s" % (when(report["started"]), when(report["last"]))
    print(head)
    if not runs:
        print("  no hook counts in its state: it was written by a version before 2.5.0")
    for key, label in HOOK_LABELS if runs else ():
        n = runs.get(key, 0)
        if not n:
            print("  %-15s never ran" % label)
            continue
        extra = ""
        if key == "session_start" and report["compactions"]:
            extra = " (%d after a compaction)" % report["compactions"]
        print("  %-15s %d run(s), %d with a message%s" % (label, n, said.get(key, 0), extra))
    if surfaced:
        print("Notes surfaced (%d): %s" % (len(surfaced), ", ".join(surfaced)))
        if report["updated"]:
            print("  updated in the vault since the session started: %s" % ", ".join(report["updated"]))
        if report["not_updated"]:
            print("  not updated: %s (fine when the change didn't alter how they work)"
                  % ", ".join(report["not_updated"]))
    else:
        print("Notes surfaced: none yet")
    if report["also_updated"]:
        print("Other notes updated: %s" % ", ".join(report["also_updated"]))
    if others > 0 and not which:
        print("(%d other session(s) in the last 24 hours; pick one with --session=ID)" % others)
    return 0


def main(argv):
    vault_opt, as_json, session = None, False, None
    it = iter(argv)
    for a in it:
        if a == "--vault":
            vault_opt = next(it, None)
        elif a == "--json":
            as_json = True
        elif a == "--session" or a.startswith("--session="):
            session = a.partition("=")[2] or ""
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
    root = vaultlib.require(root=vault_opt)
    if session is not None:
        return session_report(root, session, as_json)
    idx = vaultlib.load_index()
    cfg = vaultlib.CONFIG
    stale_days = int((cfg.get("tidy") or {}).get("stale_days") or 60)
    today = datetime.date.today()

    notes = idx["notes"]
    typed = {s: n for s, n in notes.items() if n.get("type")}
    mods = {s: n for s, n in typed.items() if n["type"] == "module"}
    full = sum(1 for n in mods.values() if n.get("depth") == "full")
    stale = []
    for s, n in typed.items():
        if n["type"] in ("release", "meta"):
            continue
        try:
            age = (today - datetime.date.fromisoformat(n.get("updated") or "")).days
        except ValueError:
            continue
        if age > stale_days:
            stale.append((age, s))
    stale.sort(reverse=True)
    by_type = {}
    for n in typed.values():
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1

    try:
        status = json.loads((root / "_meta" / "status.json").read_text())
    except (OSError, ValueError):
        status = {}
    attention = status.get("attention") or {}

    sync = []
    try:
        r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "sync.py"),
                            "--vault", str(root), "--json", "--no-fetch"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            sync = json.loads(r.stdout)
    except Exception:
        pass

    report = {
        "vault": str(root), "name": cfg.get("name") or root.name,
        "notes": len(notes), "typed": len(typed), "by_type": by_type,
        "edges": len(idx["links"]), "owned_paths": len(idx["paths"]),
        "modules": len(mods), "full": full, "stub": len(mods) - full,
        "stale_days": stale_days, "stale": [{"days": d, "note": s} for d, s in stale],
        "attention": attention,
        "attention_built_at": status.get("built_at"),
        "sync": [{"target": r.get("name"), "error": r.get("error"),
                  "commits": len(r.get("commits") or []), "files": r.get("files", 0),
                  "notes": sorted((r.get("by_note") or {}).keys()),
                  "unmatched": len(r.get("unmatched") or [])} for r in sync],
    }
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("%s — %s" % (report["name"], root))
    print("notes %d (%s) · %d reasoned links · %d owned paths" % (
        len(notes), ", ".join("%s %d" % kv for kv in sorted(by_type.items())), len(idx["links"]), len(idx["paths"])))
    print("modules %d: %d full, %d stub" % (len(mods), full, len(mods) - full))
    if stale:
        print("stale (> %d days): %d — %s" % (stale_days, len(stale),
              ", ".join("%s (%dd)" % (s, d) for d, s in stale[:6]) + (" …" if len(stale) > 6 else "")))
    else:
        print("stale (> %d days): none" % stale_days)
    count = int(attention.get("count") or 0)
    if count:
        print("attention: %d — %s  (details: _meta/Attention.md; fix with /lightkeeper:tidy)" % (
            count, "; ".join(attention.get("top") or [])))
    elif status:
        print("attention: nothing (as of %s)" % (status.get("built_at") or "?")[:16])
    else:
        print("attention: not computed yet — run `vault check --write`")
    for s in report["sync"]:
        if s["error"]:
            print("sync %s: %s" % (s["target"], s["error"]))
        elif not s["commits"] and not s["files"]:
            print("sync %s: current" % s["target"])
        else:
            print("sync %s: behind by %d commit(s), %d file(s); notes to review: %s%s" % (
                s["target"], s["commits"], s["files"], ", ".join(s["notes"][:6]) or "none",
                ("; %d file(s) match no note" % s["unmatched"]) if s["unmatched"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
