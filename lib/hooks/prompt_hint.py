#!/usr/bin/env python3
"""UserPromptSubmit hook: match the prompt against note NAMES/ALIASES/FLAGS
(tier 1 only, never content grep: precision over recall) and surface up to
three notes the agent should read before working on those areas. A prompt
that sounds like a decision or a ruling gets a one-line nudge, once per
session, to record the why in 6 Decisions/.

Each note is suggested at most once per session (state shared with the
pre-edit file guard). Silent when nothing new matches."""
import re
from pathlib import Path

import _util
import vaultlib

MAX_NOTES = 3
MAX_NEIGHBORS = 2
DECISION = re.compile(
    r"\b(client (said|wants|asked|decided|confirmed)|we (decided|agreed)|"
    r"decided to|ruling|reversed the|from now on|going forward)\b", re.I)


def run(payload):
    prompt = payload.get("prompt") or ""
    if len(prompt) < 15 or prompt.lstrip().startswith("/"):
        return
    session = payload.get("session_id", "unknown")
    state = _util.load_state(session)
    seen = set(state.get("seen", []))
    lines = []

    idx = _util.get_index()
    fresh = []
    for stem, matched_by, _score in vaultlib.match_terms(idx, prompt, tier1_only=True):
        if stem not in seen:
            fresh.append((stem, matched_by))
        if len(fresh) >= MAX_NOTES:
            break
    if fresh:
        lines.append("Knowledge-vault notes likely relevant — read before changing these "
                     "areas (vault: %s):" % vaultlib.VAULT_ROOT)
        for stem, _mb in fresh:
            note = idx["notes"][stem]
            summary = (" — " + note["summary"]) if note["summary"] else ""
            lines.append("- %s (%s, updated %s)%s" % (stem, note["path"],
                                                      note["updated"] or "?", summary))
            nbrs = vaultlib.neighbors(idx, stem, MAX_NEIGHBORS)
            if nbrs:
                bits = []
                for d, other, reason in nbrs:
                    r = (": " + vaultlib.trim(reason, 70)) if reason else ""
                    bits.append("%s %s%s" % (d, other, r))
                lines.append("  connects %s" % "; ".join(bits))
        lines.append("More: %s <terms|--paths files>" % _util.cli("find"))
        seen.update(stem for stem, _ in fresh)
        state["seen"] = sorted(seen)

    if DECISION.search(prompt) and not state.get("decision_hint_sent"):
        state["decision_hint_sent"] = True
        lines.append("This sounds like a decision or a ruling. Record the why in 6 Decisions/ "
                     "(template: _templates/Decision.md) — the why is the part that dies first.")

    if not lines:
        return
    _util.save_state(session, state)
    _util.emit_context("UserPromptSubmit", "\n".join(lines))
