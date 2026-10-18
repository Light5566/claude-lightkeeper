#!/usr/bin/env python3
"""vault log <note>: that note's history in the vault's own git log.

    vault log Invoice            # dates and subjects of every commit touching the note
    vault log Invoice -p         # with patches
    vault log --vault PATH <note>
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402


def main(argv):
    vault_opt, extra, terms = None, [], []
    it = iter(argv)
    for a in it:
        if a == "--vault":
            vault_opt = next(it, None)
        elif a.startswith("-"):
            extra.append(a)
        else:
            terms.append(a)
    root = vaultlib.require(root=vault_opt)
    if not terms:
        print(__doc__.strip())
        return 0
    idx = vaultlib.load_index()
    name = " ".join(terms)
    stem = name if name in idx["notes"] else idx["aliases"].get(name.lower())
    if not stem:
        ranked = vaultlib.match_terms(idx, name, tier1_only=True)
        if not ranked:
            sys.exit("no note named %r (try: vault find %s)" % (name, name))
        stem = ranked[0][0]
    path = idx["notes"][stem]["path"]
    print("%s — %s" % (stem, path))
    cmd = ["git", "-C", str(root), "log", "--follow", "--date=short",
           "--format=%ad  %h  %s"] + extra + ["--", path]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
