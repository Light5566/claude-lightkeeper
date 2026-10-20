#!/usr/bin/env python3
"""vault release: the data behind a release note.

    vault release v1.4.0                  # window: previous tag .. production ref
    vault release v1.4.0 --since <ref>    # explicit window start
    vault release v1.4.0 --target api     # one repo (default: this checkout's, else all)
    vault release v1.4.0 --json

Prints, per target, the commits in the window, the changed files grouped by
owning note, the files matching no note, the version-log lines added, and the
notes whose `updated` predates the window (the sweep). If a tag or ref named
after the version exists and is not on the production ref, says so: a release
note describes production. Writes nothing; /lightkeeper:release drafts the note.
"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402
import sync  # noqa: E402


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def previous_tag(repo, version, ref):
    """The newest tag reachable from ref that is not this version."""
    out = git(repo, "tag", "--merged", ref, "--sort=-creatordate")
    for tag in (out or "").splitlines():
        if tag.strip() and tag.strip() not in (version, "v" + version.lstrip("v")):
            return tag.strip()
    return None


def main(argv):
    opts = {"version": None, "since": None, "json": False, "vault": None, "targets": []}
    it = iter(argv)
    for a in it:
        if a == "--since":
            opts["since"] = next(it, None)
        elif a == "--json":
            opts["json"] = True
        elif a == "--vault":
            opts["vault"] = next(it, None)
        elif a == "--target":
            opts["targets"].append(next(it, None))
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        elif not opts["version"]:
            opts["version"] = a
    if not opts["version"]:
        print(__doc__.strip())
        return 2
    vaultlib.require(root=opts["vault"])
    state = sync.load_state()
    targets = [t for t in state["targets"] if not opts["targets"] or t["name"] in opts["targets"]]
    if not opts["targets"] and vaultlib.PROJECT_ROOT:
        here = os.path.realpath(vaultlib.PROJECT_ROOT)
        mine = [t for t in targets if os.path.realpath(os.path.expanduser(t.get("path", ""))) == here]
        if mine:
            targets = mine
    idx = vaultlib.load_index()
    reports = []
    for t in targets:
        repo, ref = t["path"], t["ref"]
        since = opts["since"] or previous_tag(repo, opts["version"], ref)
        if not since:
            reports.append({"name": t["name"], "error": "no previous tag found; pass --since <ref>"})
            continue
        r = sync.window_report(t, idx, from_override=since, fetch=False)
        r["version"] = opts["version"]
        r["since"] = since
        tag_sha = git(repo, "rev-parse", "--verify", "-q", opts["version"] + "^{commit}")
        if tag_sha:
            on_prod = git(repo, "merge-base", "--is-ancestor", tag_sha, ref) is not None
            r["version_on_production"] = on_prod
        # the sweep: owning notes whose `updated` predates the window start
        start_date = git(repo, "log", "-1", "--format=%ad", "--date=short", since) or ""
        sweep = []
        for stem in (r.get("by_note") or {}):
            note = idx["notes"].get(stem) or {}
            if note.get("updated") and start_date and note["updated"] < start_date:
                sweep.append({"note": stem, "updated": note["updated"]})
        r["window_start_date"] = start_date
        r["sweep"] = sorted(sweep, key=lambda x: x["updated"])
        reports.append(r)
    if opts["json"]:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return 0
    for r in reports:
        if r.get("error"):
            print("== %s: %s" % (r["name"], r["error"]))
            continue
        print("== %s — %s: %s..%s (%s..)" % (r["name"], r["version"], r["since"][:12], r["head"][:10], r["window_start_date"]))
        if r.get("version_on_production") is False:
            print("  WARNING: %s is not on %s — a release note describes production" % (r["version"], r.get("version_log", "the production ref")))
        sync.print_report(r)
        if r["sweep"]:
            print("  sweep — notes whose `updated` predates the window (missed when their code changed):")
            for s in r["sweep"]:
                print("    %-32s updated %s" % (s["note"], s["updated"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
