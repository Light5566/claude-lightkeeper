#!/usr/bin/env python3
"""Vault catch-up report: what landed on the repos that the vault hasn't seen.

The hooks keep the vault honest for THIS machine's sessions; work pushed by
anyone else arrives with no hook pointed at the vault. This tool reports that
delta so the vault-sync ritual (the `vault-sync` skill) can close it.

    vault sync                     # report: this checkout's target, else all
    vault sync backend             # one target by name
    vault sync --from <ref>        # override the window start (report only)
    vault sync --advance           # move cursors to the fetched heads
                                   #   (run ONLY after the notes are updated)
    vault sync --seed              # first-run: set cursors to heads, no report
    vault sync --json              # machine-readable
    vault sync --brief             # one short block per target, silent when current
    vault sync --no-fetch          # skip the fetch (use the refs already here)
    vault sync --ref <ref>         # report against this ref instead of the target's
    vault sync --vault PATH        # the vault to use (default: the one covering the cwd)

State lives in _meta/sync-state.json (tracked: it IS the claim "the vault is
current with repo X as of SHA Y", and it changes only inside a sync run that
ends in a vault commit). A target may name a `version_log` file (for example
CHANGELOG.md); lines it gained in the window are reported so the release
history is read, not guessed. `noise_files` in vault.json extends the skip list.
Stdlib only, Python 3.9.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402

MAX_COMMITS_SHOWN = 40
MAX_FILES_PER_NOTE = 12
NOISE_PREFIXES = (".claude/", ".github/", "docs/", "lang/", "storage/", "public/", "vendor/", "node_modules/")
NOISE_FILES = {"composer.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
               "Cargo.lock", "go.sum", ".gitignore", "README.md", "CLAUDE.md", "AGENTS.md",
               ".prettierrc", "eslint.config.mjs", "postcss.config.mjs", "jsconfig.json", "tsconfig.json"}
MAX_VERSION_LOG_LINES = 40


def state_path():
    return vaultlib.VAULT_ROOT / "_meta" / "sync-state.json"


def noise_files():
    return NOISE_FILES | set(vaultlib.CONFIG.get("noise_files") or [])


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo] + list(args),
                           capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout
    except Exception as e:
        return 1, str(e)


def load_state():
    try:
        return json.loads(state_path().read_text())
    except (OSError, ValueError):
        sys.exit("unusable %s — restore it or re-seed with --seed" % state_path())


def save_state(state):
    state_path().write_text(json.dumps(state, indent=2) + "\n")


def head_of(target, fetch=True, ref_override=None):
    if fetch:
        rc, _ = git(target["path"], "fetch", "origin", "--quiet")
        if rc != 0:
            print("  (fetch failed — reporting against the local ref)", file=sys.stderr)
    rc, out = git(target["path"], "rev-parse", ref_override or target["ref"])
    return out.strip() if rc == 0 else None


def window_report(target, idx, from_override=None, fetch=True, ref_override=None):
    repo, ref = target["path"], ref_override or target["ref"]
    head = head_of(target, fetch=fetch, ref_override=ref_override)
    if not head:
        return {"name": target["name"], "error": "cannot resolve %s" % ref}
    start = from_override or target.get("last")
    if not start:
        return {"name": target["name"], "error": "no cursor — run --seed first", "head": head}
    rc, _ = git(repo, "cat-file", "-e", start + "^{commit}")
    if rc != 0:
        return {"name": target["name"], "head": head,
                "error": "cursor %s unknown here (history rewritten?) — re-seed or use --from" % start[:10]}
    # origin behind (or equal to) the reconciled point: nothing new from others.
    rc, _ = git(repo, "merge-base", "--is-ancestor", head, start)
    if rc == 0:
        behind = git(repo, "rev-parse", start)[1].strip() != head
        return {"name": target["name"], "start": start, "head": head,
                "commits": [], "files": 0, "noise": 0, "by_note": {},
                "unmatched": [], "version_log_added": [],
                "note": ("origin is behind the reconciled point — nothing new has landed there"
                         if behind else None)}
    rc, out = git(repo, "log", "--no-merges", "--pretty=format:%h %ad %an: %s",
                  "--date=short", "%s..%s" % (start, head))
    commits = [l for l in out.splitlines() if l.strip()] if rc == 0 else []
    rc, out = git(repo, "diff", "--name-only", "%s..%s" % (start, head))
    files = [f for f in out.splitlines() if f.strip()] if rc == 0 else []

    interesting, noise = [], 0
    for f in files:
        base = f.rsplit("/", 1)[-1]
        if f.startswith(NOISE_PREFIXES) or base in noise_files():
            noise += 1
        else:
            interesting.append(f)
    by_note, unmatched = {}, []
    for f in interesting:
        owners = [s for s, _v, prio in vaultlib.match_paths(idx, [f]) if prio < 3]
        if owners:
            for s in owners[:2]:
                by_note.setdefault(s, []).append(f)
        else:
            unmatched.append(f)

    version_log_added = []
    vlog = target.get("version_log")
    if vlog and (Path(repo) / vlog).exists():
        rc, out = git(repo, "diff", "%s..%s" % (start, head), "--", vlog)
        version_log_added = [l[1:] for l in out.splitlines()
                             if l.startswith("+") and not l.startswith("+++")][:MAX_VERSION_LOG_LINES]

    return {"name": target["name"], "start": start, "head": head,
            "commits": commits, "files": len(files), "noise": noise,
            "by_note": {k: sorted(v) for k, v in sorted(by_note.items())},
            "unmatched": sorted(unmatched), "version_log_added": version_log_added,
            "version_log": vlog}


def print_report(r):
    print("== %s ==" % r["name"])
    if r.get("error"):
        print("  ERROR:", r["error"])
        return
    if r["start"] == r["head"] or not r["commits"] and r["files"] == 0:
        print("  vault is current (%s at %s)%s"
              % (r["name"], r["head"][:10],
                 " — " + r["note"] if r.get("note") else ""))
        return
    print("  window %s..%s — %d commit(s), %d file(s) (%d noise skipped)"
          % (r["start"][:10], r["head"][:10], len(r["commits"]), r["files"], r["noise"]))
    for c in r["commits"][:MAX_COMMITS_SHOWN]:
        print("   ", c)
    if len(r["commits"]) > MAX_COMMITS_SHOWN:
        print("    … +%d more commits" % (len(r["commits"]) - MAX_COMMITS_SHOWN))
    if r["by_note"]:
        print("  notes to review (file → owning note via the index):")
        for stem, fs in r["by_note"].items():
            shown = ", ".join(fs[:MAX_FILES_PER_NOTE])
            more = "" if len(fs) <= MAX_FILES_PER_NOTE else " (+%d)" % (len(fs) - MAX_FILES_PER_NOTE)
            print("    %-32s %s%s" % (stem, shown, more))
    if r["unmatched"]:
        print("  files matching NO note (new module or undocumented surface?):")
        for f in r["unmatched"][:25]:
            print("    %s" % f)
        if len(r["unmatched"]) > 25:
            print("    … +%d more" % (len(r["unmatched"]) - 25))
    if r.get("version_log_added"):
        print("  %s (version log) gained %s line(s) in the window — read them:"
              % (r.get("version_log"), "%d+" % MAX_VERSION_LOG_LINES
                 if len(r["version_log_added"]) >= MAX_VERSION_LOG_LINES
                 else len(r["version_log_added"])))
        for l in r["version_log_added"][:12]:
            print("    |", l)


def print_brief(r):
    """One short block, or nothing at all when that target is current. Written for
    the git post-merge hook: it must never bury a merge in output."""
    if r.get("error"):
        print("vault-sync: %s — %s" % (r["name"], r["error"]))
        return
    if not r["commits"] and not r["files"]:
        return
    notes = list(r["by_note"])
    shown = ", ".join(notes[:6]) + (" (+%d more)" % (len(notes) - 6) if len(notes) > 6 else "")
    print("vault is behind %s: %s..%s — %d commit(s), %d file(s)"
          % (r["name"], r["start"][:10], r["head"][:10], len(r["commits"]), r["files"]))
    if notes:
        print("  notes to review: %s" % shown)
    extra = []
    if r["unmatched"]:
        extra.append("%d file(s) match no note" % len(r["unmatched"]))
    if r.get("version_log_added"):
        extra.append("%s gained %d line(s)" % (r.get("version_log"), len(r["version_log_added"])))
    if extra:
        print("  %s" % " · ".join(extra))
    print("  catch it up with the vault-sync skill (or: ask Claude to sync the vault)")


def main(argv):
    opts = {"advance": False, "seed": False, "json": False, "from": None,
            "brief": False, "fetch": True, "ref": None, "names": [], "vault": None}
    it = iter(argv)
    for a in it:
        if a == "--vault":
            opts["vault"] = next(it, None)
        elif a == "--advance":
            opts["advance"] = True
        elif a == "--seed":
            opts["seed"] = True
        elif a == "--json":
            opts["json"] = True
        elif a == "--from":
            opts["from"] = next(it, None)
        elif a == "--brief":
            opts["brief"] = True
        elif a == "--no-fetch":
            opts["fetch"] = False
        elif a == "--ref":
            opts["ref"] = next(it, None)
        elif a in ("-h", "--help"):
            print(__doc__.strip()); return 0
        else:
            opts["names"].append(a)

    vaultlib.require(root=opts["vault"])
    state = load_state()
    targets = [t for t in state["targets"]
               if not opts["names"] or t["name"] in opts["names"]]
    if not opts["names"] and vaultlib.PROJECT_ROOT:
        # run from inside a covered checkout: default to that checkout's target
        here = os.path.realpath(vaultlib.PROJECT_ROOT)
        mine = [t for t in targets
                if t.get("path") and os.path.realpath(os.path.expanduser(t["path"])) == here]
        if mine:
            targets = mine
    if not targets:
        sys.exit("no matching targets (have: %s)"
                 % ", ".join(t["name"] for t in state["targets"]))

    if opts["seed"] or opts["advance"]:
        for t in targets:
            head = head_of(t)
            if not head:
                continue
            last = t.get("last")
            if opts["advance"] and last:
                rc, _ = git(t["path"], "merge-base", "--is-ancestor", head, last)
                if rc == 0 and head != last:
                    print("%s cursor stays at %s (origin is behind it — never regress)"
                          % (t["name"], last[:10]))
                    continue
            t["last"] = head
            print("%s cursor -> %s" % (t["name"], head[:10]))
        save_state(state)
        if opts["advance"]:
            print("cursors advanced — commit the vault (sync-state.json is tracked).")
        return 0

    idx = vaultlib.load_index()
    reports = [window_report(t, idx, opts["from"], fetch=opts["fetch"],
                             ref_override=opts["ref"]) for t in targets]
    if opts["json"]:
        print(json.dumps(reports, ensure_ascii=False))
    elif opts["brief"]:
        for r in reports:
            print_brief(r)
    else:
        for r in reports:
            print_report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
