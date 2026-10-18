#!/usr/bin/env python3
"""vault status: the vault on one screen.

    vault status            coverage, stale notes, attention signals, sync drift
    vault status --json
    vault status --vault PATH

Reads the index (rebuilt if notes changed), _meta/status.json (written by
`vault check --write`) and runs the sync report without fetching.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402


def main(argv):
    vault_opt, as_json = None, False
    it = iter(argv)
    for a in it:
        if a == "--vault":
            vault_opt = next(it, None)
        elif a == "--json":
            as_json = True
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
    root = vaultlib.require(root=vault_opt)
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
        print("attention: %d — %s  (details: _meta/Attention.md; fix with /vault:tidy)" % (
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
