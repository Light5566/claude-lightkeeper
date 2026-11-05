#!/usr/bin/env python3
"""Render the PR comment: which vault notes own the files a pull request changed.

    python3 pr_notes.py --vault <vault dir> --files <list, one path per line> [--repo <checkout>]

Prints markdown to stdout. Never exits non-zero: when the vault cannot be read
the comment says so instead. Stdlib only; imports the plugin's own lib/.
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

MARKER = "<!-- claude-vault -->"
MAX_FILES_PER_NOTE = 8
MAX_UNMATCHED = 20
MAX_DETAIL_NOTES = 6
MAX_LINKS = 3
WIKILINK_TEXT = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")


def plain(text, n):
    """Note text for a PR comment: wikilinks as plain names, and no @mentions
    (an `@Transactional` in a Gotcha would otherwise ping a GitHub user)."""
    import vaultlib
    return vaultlib.trim(WIKILINK_TEXT.sub(r"\1", text).replace("@", "@​"), n)


def details(vaultlib, idx, stems, vault):
    """Per owning note: its reasoned links (the blast radius) and its first Gotcha."""
    out = []
    for stem in stems:
        n = idx["notes"][stem]
        sub = ["  - %s %s%s" % (d, other, (": " + plain(reason, 140)) if reason else "")
               for d, other, reason in vaultlib.neighbors(idx, stem, MAX_LINKS)]
        try:
            gotchas = vaultlib.bullets((Path(vault) / n["path"]).read_text(encoding="utf-8"), "Gotchas")
        except OSError:
            gotchas = []
        if gotchas:
            more = len(gotchas) - 1
            sub.append("  - Gotcha: %s%s" % (plain(gotchas[0], 220),
                                            " (+%d more in the note)" % more if more else ""))
        if sub:
            summary = (" — " + plain(n["summary"], 160)) if n.get("summary") else ""
            out += ["- **%s**%s" % (stem, summary)] + sub
    return out


def noise(path):
    try:
        import sync
        base = path.rsplit("/", 1)[-1]
        return path.startswith(sync.NOISE_PREFIXES) or base in sync.NOISE_FILES
    except Exception:
        return False


def render(vault, files, repo):
    import vaultlib
    if not vault or not (Path(vault) / "_meta" / "vault.json").is_file() or not vaultlib.init(root=vault, cwd=repo):
        return ["%s\n### Knowledge vault\n\nCould not read the vault at `%s` (no `_meta/vault.json`). "
                "Nothing to report." % (MARKER, vault)]
    idx = vaultlib.load_index()
    cfg_name = vaultlib.CONFIG.get("name") or Path(vault).name
    by_note, unmatched = {}, []
    for f in files:
        if noise(f):
            continue
        owners = [s for s, _via, prio in vaultlib.match_paths(idx, [f], cwd=repo, project_dir=repo) if prio < 3]
        if owners:
            for s in owners[:2]:
                by_note.setdefault(s, []).append(f)
        else:
            unmatched.append(f)
    out = [MARKER, "### Knowledge vault: %s" % cfg_name, ""]
    if not by_note and not unmatched:
        out.append("No watched source files changed. Nothing to update in the vault.")
        return out
    if by_note:
        out += ["Files in this PR belong to these vault notes. Were they updated?", "",
                "| Note | Updated | Files |", "|---|---|---|"]
        for stem in sorted(by_note):
            n = idx["notes"][stem]
            fs = by_note[stem]
            shown = ", ".join("`%s`" % f for f in fs[:MAX_FILES_PER_NOTE])
            if len(fs) > MAX_FILES_PER_NOTE:
                shown += " (+%d)" % (len(fs) - MAX_FILES_PER_NOTE)
            out.append("| **%s** | %s | %s |" % (stem, n.get("updated") or "?", shown))
        out.append("")
        more = details(vaultlib, idx, sorted(by_note)[:MAX_DETAIL_NOTES], vault)
        if more:
            out += ["What else a change here touches, and the trap to know first:", ""] + more + [""]
    if unmatched:
        out.append("%d changed file(s) match no note (a new module, or an undocumented surface?):" % len(unmatched))
        out.append("")
        out += ["- `%s`" % f for f in unmatched[:MAX_UNMATCHED]]
        if len(unmatched) > MAX_UNMATCHED:
            out.append("- … +%d more" % (len(unmatched) - MAX_UNMATCHED))
        out.append("")
    out.append("_Posted by [Lightkeeper](https://github.com/Light5566/claude-lightkeeper). "
               "Advisory only: it never blocks a merge._")
    return out


def main(argv):
    vault, files_path, repo = None, None, os.getcwd()
    it = iter(argv)
    for a in it:
        if a == "--vault":
            vault = next(it, None)
        elif a == "--files":
            files_path = next(it, None)
        elif a == "--repo":
            repo = next(it, None)
    try:
        files = [l.strip() for l in open(files_path) if l.strip()] if files_path else []
        lines = render(vault, files, repo)
    except Exception as e:  # comment-only: report, never fail the job
        lines = [MARKER, "### Knowledge vault", "", "The vault check could not run: `%s`." % str(e)[:200]]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
