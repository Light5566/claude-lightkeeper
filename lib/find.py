#!/usr/bin/env python3
"""Vault retrieval CLI: the query door into the knowledge vault.

    vault find invoice repricing              # topic search (tiered)
    vault find --paths src/billing/invoice.py # which notes own these files
Options:
    --vault PATH   the vault to query (default: the vault covering the cwd)
    --json         machine-readable output (used by hooks/scripts)
    --limit N      max notes to print (default 5)
    --tier1-only   names/aliases/flags only, no tag/domain or content matching
    --stats        print index statistics and exit

Term search tiers: (1) note names + aliases + flags, (2) tags/domain,
(3) full-text grep over the live notes, printing the matching lines — the
top notes are 8k words, so the matching bullet IS the retrieval unit.
Reverse path lookup: exact path -> dir prefix -> class/basename.
Every hit prints its one-hop links WITH their reasons: the blast radius.

The index rebuilds automatically whenever a note changed. Always exits 0
unless the vault itself is unusable.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402


def parse_args(argv):
    opts = {"json": False, "limit": 5, "tier1_only": False, "stats": False,
            "paths": False, "terms": [], "vault": None}
    it = iter(argv)
    for a in it:
        if a == "--vault":
            opts["vault"] = next(it, None)
        elif a == "--json":
            opts["json"] = True
        elif a == "--limit":
            try:
                opts["limit"] = max(1, int(next(it)))
            except (StopIteration, ValueError):
                pass
        elif a == "--tier1-only":
            opts["tier1_only"] = True
        elif a == "--stats":
            opts["stats"] = True
        elif a == "--paths":
            opts["paths"] = True
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        else:
            opts["terms"].append(a)
    return opts


def content_grep(idx, terms, limit):
    """Tier 3: AND-match terms over live note bodies; return matching lines."""
    lterms = [t.lower() for t in terms if len(t) >= 2]
    if not lterms:
        return []
    hits = []
    for stem, note in idx["notes"].items():
        p = vaultlib.VAULT_ROOT / note["path"]
        try:
            body = p.read_text()
        except OSError:
            continue
        low = body.lower()
        if not all(t in low for t in lterms):
            continue
        lines = []
        for line in body.splitlines():
            ll = line.lower()
            n = sum(1 for t in lterms if t in ll)
            if n:
                lines.append((n, line.strip()))
        lines.sort(key=lambda t: -t[0])
        best = [re.sub(r"\s+", " ", l)[:200] for _, l in lines[:2]]
        score = sum(n for n, _ in lines)
        hits.append((score, stem, best))
    hits.sort(key=lambda t: -t[0])
    return [(stem, lines) for _, stem, lines in hits[:limit]]


def render_note(idx, stem, matched_by=None, matched_lines=None):
    note = idx["notes"][stem]
    meta_bits = "/".join(x for x in (note["type"], note["status"], note["depth"]) if x)
    head = "%s  (%s, updated %s)" % (stem, meta_bits, note["updated"] or "?")
    if matched_by:
        head += "   [%s]" % matched_by
    lines = [head]
    if note["summary"]:
        lines.append("  %s" % note["summary"])
    lines.append("  → %s" % note["path"])
    for ml in matched_lines or []:
        lines.append("  match: %s" % ml)
    nbrs = vaultlib.neighbors(idx, stem)
    if nbrs:
        lines.append("  connects:")
        for d, other, reason in nbrs:
            r = (" — " + vaultlib.trim(reason, 120)) if reason else ""
            lines.append("    %s %s%s" % (d, other, r))
    return "\n".join(lines)


def as_json(idx, stems_with_via, matched_lines=None):
    out = []
    for stem, via in stems_with_via:
        note = idx["notes"][stem]
        out.append({
            "stem": stem,
            "path": note["path"],
            "type": note["type"],
            "status": note["status"],
            "depth": note["depth"],
            "updated": note["updated"],
            "summary": note["summary"],
            "matched_by": via,
            "matched_lines": (matched_lines or {}).get(stem, []),
            "neighbors": [
                {"dir": d, "stem": o, "reason": r}
                for d, o, r in vaultlib.neighbors(idx, stem)
            ],
        })
    return out


def main(argv):
    opts = parse_args(argv)
    vaultlib.require(root=opts["vault"])
    try:
        idx = vaultlib.load_index()
    except Exception as e:  # unusable vault is the one real failure
        print("vault index unavailable: %s" % e, file=sys.stderr)
        return 1

    if opts["stats"]:
        by_type = {}
        for n in idx["notes"].values():
            by_type[n["type"] or "?"] = by_type.get(n["type"] or "?", 0) + 1
        stats = {
            "notes": idx["note_count"],
            "by_type": dict(sorted(by_type.items())),
            "edges": len(idx["links"]),
            "paths": len(idx["paths"]),
            "classes": len(idx["classes"]),
            "aliases": len(idx["aliases"]),
            "built_at": idx["built_at"],
        }
        print(json.dumps(stats, indent=2) if opts["json"] else
              "\n".join("%s: %s" % (k, v) for k, v in stats.items()))
        return 0

    if not opts["terms"]:
        print(__doc__.strip())
        return 0

    if opts["paths"]:
        matches = vaultlib.match_paths(idx, opts["terms"])
        picked = [(s, via) for s, via, _prio in matches[: opts["limit"]]]
        if opts["json"]:
            print(json.dumps({"query": opts["terms"], "mode": "paths",
                              "matches": as_json(idx, picked)}, ensure_ascii=False))
        elif not picked:
            print("no vault note claims these paths — if this area is real, it may need a note")
        else:
            print("\n\n".join(render_note(idx, s, via) for s, via in picked))
        return 0

    query = " ".join(opts["terms"])
    ranked = vaultlib.match_terms(idx, query, tier1_only=opts["tier1_only"])
    picked = [(s, mb) for s, mb, _score in ranked[: opts["limit"]]]
    matched_lines = {}
    if not picked and not opts["tier1_only"]:
        for stem, lines in content_grep(idx, opts["terms"], opts["limit"]):
            picked.append((stem, "content"))
            matched_lines[stem] = lines
    if opts["json"]:
        print(json.dumps({"query": query, "mode": "terms",
                          "matches": as_json(idx, picked, matched_lines)},
                         ensure_ascii=False))
    elif not picked:
        print("no matches — try fewer/other words, or --paths for file lookup")
    else:
        print("\n\n".join(
            render_note(idx, s, mb, matched_lines.get(s)) for s, mb in picked))
        if matched_lines and len(opts["terms"]) <= 3:
            # Names and aliases missed but the body matched: the vocabulary gap is
            # the fix. Offer it so the next query (and the prompt hook) match by name.
            print("\nTip: if one of these is what you meant by %r, add it to that "
                  "note's frontmatter — aliases: [%s] — so names match next time."
                  % (query, query))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
