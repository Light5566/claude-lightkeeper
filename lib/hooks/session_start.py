#!/usr/bin/env python3
"""SessionStart hook: a short static primer telling the agent the vault exists
and how to query it. No index load: this must be near-instant. Silent on
resume (the primer is already in the transcript); after a compaction
(source "compact") it sends a one-line reminder instead of the full primer.
Once per 24h it also surfaces the maintenance signals from _meta/status.json."""
import json
import time
from pathlib import Path

import _util
import vaultlib

ATTENTION_EVERY = 24 * 3600


def attention_line():
    try:
        status = json.loads((vaultlib.VAULT_ROOT / "_meta" / "status.json").read_text())
    except (OSError, ValueError):
        return None
    att = status.get("attention") or {}
    count = int(att.get("count") or 0)
    if count <= 0:
        return None
    st = _util.vault_state()
    if time.time() - float(st.get("attention_at") or 0) < ATTENTION_EVERY:
        return None
    st["attention_at"] = time.time()
    _util.save_vault_state(st)
    top = "; ".join((att.get("top") or [])[:3])
    return ("%d note(s) need attention%s — run /lightkeeper:tidy when convenient "
            "(details: _meta/Attention.md)." % (count, (" (%s)" % top) if top else ""))


def run(payload):
    source = payload.get("source")
    if source == "resume":
        return
    name = vaultlib.CONFIG.get("name") or vaultlib.VAULT_ROOT.name
    find = _util.cli("find")
    if source == "compact":
        _util.emit_context("SessionStart",
                           "Context was just compacted. The %s knowledge vault is still your "
                           "retrieval layer: before touching an area again, `%s <module words>` or "
                           "`%s --paths <files>` instead of re-exploring code you already read."
                           % (name, find, find))
        return
    repo = vaultlib.MATCHED_REPO[0] if vaultlib.MATCHED_REPO else "this project"
    lines = [
        "%s knowledge vault — the world map of %s (module notes with How-it-works/Gotchas, "
        "flows, integrations, platform traps, decisions): %s" % (name, repo, vaultlib.VAULT_ROOT),
        "It is your retrieval layer. BEFORE major or cross-module work, query it instead of "
        "re-exploring code:",
        "  %s <module words>     # topic search + blast radius" % find,
        "  %s --paths <files>    # which notes own these files" % find,
        "Read a matched note's 'How it works' + 'Gotchas' before changing that area; its "
        "'Connects to' reasons are the blast radius. After a meaningful change, update the "
        "affected note (knowledge-vault skill): that is part of the definition of done. "
        "Learned a trap while debugging? Write the Gotcha even if no file changed.",
    ]
    extra = attention_line()
    if extra:
        lines.append(extra)
    _util.emit_context("SessionStart", "\n".join(lines))
