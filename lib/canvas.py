#!/usr/bin/env python3
"""Generate a JSON Canvas overview of a vault from its index.

One group per domain, the domain's module notes as file nodes inside it, and
cross-domain links as labelled edges. Pure functions over the index dict;
``main`` is the CLI. Output is deterministic: an unchanged vault produces an
identical file.

    python3 lib/canvas.py --vault <path> [--out World.canvas]
    python3 lib/canvas.py --vault <path> --index <index.json>   # bypass vaultlib
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

NODE_W, NODE_H = 300, 130       # file node size
PITCH_X, PITCH_Y = 350, 180     # node spacing inside a group
PAD = 45                        # group padding
PER_ROW = 4                     # nodes per row inside a group
GROUP_GAP_X, GROUP_GAP_Y = 300, 150
MAX_ROW_W = 3600                # groups wrap to a new row past this width
UNASSIGNED = "Unassigned"       # group for modules with no domain
MAX_EDGES_PER_NODE = 4
LABEL_LEN = 60


def slug(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower()) or "x"


def trim(text, n):
    """Cut at a word boundary with an ellipsis."""
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return (cut or text[:n]) + "…"


def group_modules(idx):
    """{domain: [stem, ...]} for module notes, stems sorted; no domain -> UNASSIGNED."""
    groups = {}
    for stem, note in idx["notes"].items():
        if note.get("type") == "module":
            groups.setdefault(note.get("domain") or UNASSIGNED, []).append(stem)
    for stems in groups.values():
        stems.sort()
    return groups


def build_canvas(idx):
    """Index dict -> JSON Canvas dict (nodes + edges)."""
    groups = group_modules(idx)
    names = sorted(groups, key=lambda g: (g == UNASSIGNED, g))  # catch-all last
    nodes, edges = [], []
    node_id, group_of, ids = {}, {}, set()

    def uniq(base):
        cand, i = base, 2
        while cand in ids:
            cand, i = "%s%d" % (base, i), i + 1
        ids.add(cand)
        return cand

    x = y = row_h = 0
    for gi, name in enumerate(names):
        stems = groups[name]
        cols = min(PER_ROW, len(stems))
        rows = (len(stems) + PER_ROW - 1) // PER_ROW
        w = 2 * PAD + cols * PITCH_X - (PITCH_X - NODE_W)
        h = 2 * PAD + rows * PITCH_Y - (PITCH_Y - NODE_H)
        if x and x + w > MAX_ROW_W:
            x, y, row_h = 0, y + row_h + GROUP_GAP_Y, 0
        nodes.append({"id": uniq("g_" + slug(name)), "type": "group", "label": name,
                      "color": str(gi % 6 + 1), "x": x, "y": y, "width": w, "height": h})
        for i, stem in enumerate(stems):
            node_id[stem], group_of[stem] = uniq("n_" + slug(stem)), name
            nodes.append({"id": node_id[stem], "type": "file", "file": idx["notes"][stem]["path"],
                          "x": x + PAD + (i % PER_ROW) * PITCH_X,
                          "y": y + PAD + (i // PER_ROW) * PITCH_Y,
                          "width": NODE_W, "height": NODE_H})
        x += w + GROUP_GAP_X
        row_h = max(row_h, h)

    # Cross-group module links only; reasoned edges first, then by target name,
    # one edge per (source, target), capped per source.
    cand = sorted(
        ((e["from"], e["to"], e.get("reason")) for e in idx["links"]
         if e["from"] in node_id and e["to"] in node_id
         and group_of[e["from"]] != group_of[e["to"]]),
        key=lambda t: (t[0], t[2] is None, t[1], t[2] or ""))
    seen, per_src = set(), {}
    for src, dst, reason in cand:
        if (src, dst) in seen or per_src.get(src, 0) >= MAX_EDGES_PER_NODE:
            continue
        seen.add((src, dst))
        per_src[src] = per_src.get(src, 0) + 1
        edge = {"id": "e%d" % len(edges), "fromNode": node_id[src], "fromSide": "right",
                "toNode": node_id[dst], "toSide": "left"}
        if reason:
            edge["label"] = trim(reason, LABEL_LEN)
        edges.append(edge)
    return {"nodes": nodes, "edges": edges}


def render(canvas):
    return json.dumps(canvas, ensure_ascii=False, indent="\t") + "\n"


def load_index(vault_root, index_path=None):
    if index_path:
        return json.loads(Path(index_path).read_text(encoding="utf-8"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vaultlib
    return vaultlib.load_index(vault_root)


def _selftest():
    idx = {"notes": {
        "A": {"type": "module", "domain": "One", "path": "m/A.md"},
        "E": {"type": "module", "domain": "One", "path": "m/E.md"},
        "B": {"type": "module", "domain": "Two", "path": "m/B.md"},
        "C": {"type": "module", "domain": "", "path": "m/C.md"},
        "D": {"type": "flow", "domain": "One", "path": "f/D.md"},
    }, "links": [
        {"from": "A", "to": "B", "reason": "word " * 30},
        {"from": "A", "to": "B", "reason": "duplicate pair"},
        {"from": "B", "to": "A", "reason": None},
        {"from": "A", "to": "E", "reason": "same group"},
        {"from": "A", "to": "D", "reason": "not a module"},
    ]}
    c = build_canvas(idx)
    groups = [n for n in c["nodes"] if n["type"] == "group"]
    assert [g["label"] for g in groups] == ["One", "Two", UNASSIGNED], groups
    assert (groups[0]["width"], groups[0]["height"]) == (740, 220), groups[0]
    files = [n for n in c["nodes"] if n["type"] == "file"]
    assert [n["file"] for n in files] == ["m/A.md", "m/E.md", "m/B.md", "m/C.md"], files
    assert (files[0]["x"], files[0]["y"], files[1]["x"]) == (PAD, PAD, PAD + PITCH_X), files
    assert [(e["fromNode"], e["toNode"]) for e in c["edges"]] == [("n_a", "n_b"), ("n_b", "n_a")], c["edges"]
    assert len(c["edges"][0]["label"]) <= LABEL_LEN + 1 and "label" not in c["edges"][1]
    assert render(c) == render(build_canvas(idx))
    print("canvas selftest ok")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vault", type=Path, help="vault root")
    ap.add_argument("--index", help="read this index.json instead of loading via vaultlib")
    ap.add_argument("--out", type=Path, help="output file (default: <vault>/World.canvas)")
    ap.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.vault and not (args.index and args.out):
        ap.error("--vault is required (or --index together with --out)")
    canvas = build_canvas(load_index(args.vault, args.index))
    out = args.out or args.vault / "World.canvas"
    out.write_text(render(canvas), encoding="utf-8")
    groups = sum(1 for n in canvas["nodes"] if n["type"] == "group")
    print("%s: %d groups, %d nodes, %d edges" % (out, groups, len(canvas["nodes"]) - groups, len(canvas["edges"])))


if __name__ == "__main__":
    main()
