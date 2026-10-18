#!/usr/bin/env python3
"""Vault health check + Coverage.md / index.json regeneration.

    vault check                 # report only
    vault check --write         # also regenerate _meta/Coverage.md and the
                                # search index _meta/index.json
    vault check --vault PATH    # the vault to check (default: the one covering the cwd)

Only notes that carry a `type:` in their frontmatter are linted, so an existing
vault can be adopted gradually: untyped notes are indexed for search and
nothing else. Checks:
  1. Every [[wikilink]] resolves to a real note or a declared alias
     (code spans and fences ignored).
  2. No two notes share a filename (which would make [[links]] ambiguous).
  3. Every [[link]] in a relationship section carries a reason (the one rule),
     and no Where-it-lives cell claims a container dir like `app/Services/`.
  4. Frontmatter values are on-schema (type/status/depth/repo), and
     `aliases:` values are well-formed flat lists with no collisions.
  5. Notes with no inbound links (orphans).
  6. Notes whose `updated:` is older than the configured stale window.
  7. Nothing that looks like a secret or personal data (emails, long digit
     runs, API-key shapes, private keys).
"""
import collections
import datetime
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vaultlib  # noqa: E402
from vaultlib import frontmatter, iter_notes, parse_inline_list, strip_code  # noqa: E402

import re  # noqa: E402

# Entry points and per-version records legitimately have no inbound links.
ORPHAN_OK = {"Home"}
SECRET_PATTERNS = [
    ("email address", re.compile(r"[\w.+-]+@(?!example\.(?:com|org|net)|users\.noreply\.github\.com)[\w-]+\.[\w.-]+")),
    ("long digit run (id / phone / card?)", re.compile(r"(?<![\w./-])\d{9,}(?![\w./-])")),
    ("API-key shape", re.compile(r"\b(?:sk|pk|rk)[-_](?:live|test|proj)?[-_]?[A-Za-z0-9]{16,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY")),
]


def parse_args(argv):
    opts = {"write": False, "vault": None}
    it = iter(argv)
    for a in it:
        if a == "--write":
            opts["write"] = True
        elif a == "--vault":
            opts["vault"] = next(it, None)
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
    return opts


def main(argv=None):
    opts = parse_args(sys.argv[1:] if argv is None else argv)
    root = vaultlib.require(root=opts["vault"])
    stale_days = int((vaultlib.CONFIG.get("tidy") or {}).get("stale_days") or 60)
    all_files = sorted(iter_notes(root))
    if not all_files:
        sys.exit("No notes found under %s — is the vault intact?" % root)
    meta_all = {p: frontmatter(p.read_text()) for p in all_files}
    # typed notes are the ones this vault's conventions apply to
    files = [p for p in all_files if meta_all[p].get("type")]
    if not files:
        files = all_files

    # Obsidian links non-markdown files with their extension: [[World.canvas]], [[Coverage.base]]
    canvases = [p for p in root.rglob("*")
                if p.suffix in (".canvas", ".base") and not vaultlib.SKIP_DIRS & set(p.parts)]
    stems = {p.stem for p in all_files}
    names = stems | {p.stem for p in canvases} | {p.name for p in canvases}
    meta = {p: meta_all[p] for p in files}

    problems = 0

    # aliases join the link namespace — collect + validate them first
    ALIAS_BAD_CHARS = ("[[", "]]", "|", "#")
    alias_owners = collections.defaultdict(list)
    malformed_aliases = []
    for p in all_files:
        raw = meta_all[p].get("aliases")
        if raw is None:
            continue
        if not (raw.startswith("[") and raw.endswith("]")):
            malformed_aliases.append(
                f"{p.name}: aliases must be a flat inline list — aliases: [A, B]")
            continue
        for a in parse_inline_list(raw):
            if any(c in a for c in ALIAS_BAD_CHARS):
                malformed_aliases.append(f"{p.name}: alias {a!r} contains [[ ]] | or #")
            else:
                alias_owners[a].append(p.stem)
    alias_problems = []
    for a, owners in sorted(alias_owners.items()):
        if len(owners) > 1:
            alias_problems.append(f"alias {a!r} claimed by: {', '.join(sorted(owners))}")
        if a in stems and a not in owners:
            alias_problems.append(f"alias {a!r} on {owners[0]} shadows the note named {a!r}")
        elif a in stems:
            alias_problems.append(f"alias {a!r} on {owners[0]} duplicates its own/other note name")
    if malformed_aliases or alias_problems:
        problems += len(malformed_aliases) + len(alias_problems)
        print("ALIAS PROBLEMS (aliases join the link namespace — see Conventions)")
        for m in malformed_aliases + alias_problems:
            print(f"  {m}")
        print()
    # only clean aliases (single owner, not shadowing a real note) resolve links
    alias_names = {a for a, owners in alias_owners.items()
                   if len(owners) == 1 and a not in stems}
    alias_to_stem = {a: owners[0] for a, owners in alias_owners.items()
                     if len(owners) == 1 and a not in stems}

    # 1. unresolved links
    unresolved = collections.defaultdict(list)
    inbound = collections.Counter()
    for p in files:
        for target in re.findall(r"\[\[([^\]|#]+)", strip_code(p.read_text())):
            target = target.strip()
            inbound[alias_to_stem.get(target, target)] += 1
            if target not in names and target not in alias_names:
                unresolved[target].append(p.name)
    if unresolved:
        problems += len(unresolved)
        print("UNRESOLVED LINKS")
        for target, srcs in sorted(unresolved.items()):
            print(f"  [[{target}]]  <- {', '.join(sorted(set(srcs)))}")
        print()

    # 2. duplicate filenames make [[links]] ambiguous
    dupes = [n for n, c in collections.Counter(p.stem for p in all_files).items() if c > 1]
    if dupes:
        problems += len(dupes)
        print("DUPLICATE NOTE NAMES (ambiguous links)")
        for d in dupes:
            print(f"  {d}: {[str(p.relative_to(root)) for p in all_files if p.stem == d]}")
        print()

    # 3. the one rule: links in relationship sections must carry a reason
    LINK_SECTIONS = r"^## (?:Connects to|Modules involved|Affects|Modules touched|Flows affected)\n(.*?)(?=^## |\Z)"
    bare = []
    for p in files:
        for section in re.findall(LINK_SECTIONS, p.read_text(), re.S | re.M):
            for line in section.splitlines():
                stripped = line.strip()
                if stripped.startswith("- [[") and "—" not in stripped:
                    bare.append(f"{p.name}: {stripped}")
    if bare:
        problems += len(bare)
        print("BARE LINKS (every [[link]] must carry a reason — see Conventions)")
        for b in bare:
            print(f"  {b}")
        print()

    # 3b. a Where-it-lives cell citing a container dir (app/Services/, ...) claims
    #     nothing specific — vaultlib ignores it, so the row is dead weight and
    #     usually an unfilled template row.
    generic = []
    for p in files:
        for section in vaultlib.WHERE_SECTION.findall(p.read_text()):
            for span in vaultlib.INLINE_SPAN.findall(section):
                kind, val = vaultlib.normalize_path(span)
                if kind == "dir" and val in vaultlib.GENERIC_DIRS:
                    generic.append(f"{p.name}: `{span}`")
    if generic:
        problems += len(generic)
        print("GENERIC DIRECTORY CLAIMS (name the module's own files/folders, or delete the row)")
        for g in generic:
            print(f"  {g}")
        print()

    # 4. frontmatter vocabulary — an off-schema value silently breaks the graph queries
    VOCAB = {
        "type": {"module", "domain", "flow", "integration", "platform",
                 "decision", "release", "repo", "meta"},
        "status": {"shipped", "in-progress", "planned", "deprecated",
                   "accepted", "open", "superseded", "superseded-in-part"},
        "depth": {"full", "stub"},
    }
    repo_keys = set((vaultlib.CONFIG.get("repos") or {}).keys())
    if repo_keys:
        VOCAB["repo"] = repo_keys | {"both"}
    offschema = []
    for p in files:
        for key, allowed in VOCAB.items():
            val = meta[p].get(key)
            if val and val not in allowed:
                offschema.append(f"{p.name}: {key}: {val}  (allowed: {', '.join(sorted(allowed))})")
    if offschema:
        problems += len(offschema)
        print("OFF-SCHEMA FRONTMATTER (see Conventions)")
        for o in offschema:
            print(f"  {o}")
        print()

    # 5. orphans
    orphans = [
        p.stem for p in files
        if inbound[p.stem] == 0
        and p.stem not in ORPHAN_OK
        and meta[p].get("type") != "release"
    ]
    if orphans:
        print("ORPHANS (nothing links here)")
        for o in sorted(orphans):
            print(f"  {o}")
        print()

    # 6. stale notes
    today = datetime.date.today()
    stale = []
    for p in files:
        raw = meta[p].get("updated", "")
        try:
            age = (today - datetime.date.fromisoformat(raw)).days
        except ValueError:
            continue
        if age > stale_days:
            stale.append((age, p.stem))
    if stale:
        print(f"STALE (updated > {stale_days} days ago)")
        for age, name in sorted(stale, reverse=True):
            print(f"  {age:>4}d  {name}")
        print()

    # 7. secrets and personal data never belong in a vault that syncs to other machines
    leaks = []
    for p in files:
        text = p.read_text()
        for label, rx in SECRET_PATTERNS:
            for m in rx.finditer(text):
                leaks.append(f"{p.name}: {label}: {m.group(0)[:40]}")
                if len(leaks) > 200:
                    break
    if leaks:
        problems += len(leaks)
        print("POSSIBLE SECRETS / PERSONAL DATA (remove or replace with a placeholder)")
        for l in leaks[:40]:
            print(f"  {l}")
        if len(leaks) > 40:
            print(f"  … +{len(leaks) - 40} more")
        print()

    # coverage
    mods = [p for p in files if meta[p].get("type") == "module"]
    full = sorted(p.stem for p in mods if meta[p].get("depth") == "full")
    stub = sorted(p.stem for p in mods if meta[p].get("depth") == "stub")
    print(f"COVERAGE  modules: {len(mods)}   full: {len(full)}   stub: {len(stub)}")
    print(f"TOTAL notes: {len(files)}")

    if opts["write"]:
        write_coverage(root, meta, mods, full, stub, len(all_files))
        print("\nwrote _meta/Coverage.md")
        write_changelog(root)
        print("wrote _meta/Changelog.md")
        # Always rebuild the search index, problems or not — the hooks must
        # never run against a stale index because a link was broken.
        idx = vaultlib.build_index(root)
        vaultlib.write_index(idx, root)
        items = attention_signals(root, idx, meta_all)
        write_attention(root, items)
        print("wrote _meta/Attention.md (%d signal(s))" % len(items))
        print("wrote _meta/index.json (%d notes, %d edges, %d paths, %d classes)"
              % (idx["note_count"], len(idx["links"]), len(idx["paths"]), len(idx["classes"])))
        try:
            import canvas as canvas_mod
            (root / "World.canvas").write_text(canvas_mod.render(canvas_mod.build_canvas(idx)), encoding="utf-8")
            print("wrote World.canvas")
        except Exception as e:  # the map is a nicety; never fail the check over it
            print("World.canvas not written: %s" % e)

    return 1 if problems else 0


def write_changelog(root, limit=200):
    """Derived from the vault's own git history, never hand-kept: one line per
    commit with the notes it touched, grouped by folder; older months collapse
    to counts. Regenerated right before the vault commit, like Coverage.md."""
    today = datetime.date.today().isoformat()
    head = ["---", "type: meta", f"updated: {today}", "tags: [meta]", "---", "",
            "# Changelog", "",
            "> Regenerated by `vault check --write` from this vault's git history. Don't hand-edit.",
            ""]
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "--date=short",
                            "--format=%x1e%h%x1f%ad%x1f%s", "--name-only", "-n", str(limit)],
                           capture_output=True, text=True, timeout=30)
        raw = r.stdout if r.returncode == 0 else ""
    except Exception:
        raw = ""
    lines = []
    for block in raw.split("\x1e"):
        block = block.strip("\n")
        if not block:
            continue
        first, _, rest = block.partition("\n")
        parts = first.split("\x1f")
        if len(parts) < 3:
            continue
        sha, date, subject = parts[0], parts[1], parts[2]
        by_folder = collections.OrderedDict()
        for f in rest.splitlines():
            f = f.strip()
            if not f.endswith(".md") or f.startswith("_meta/"):
                continue
            folder, _, name = f.rpartition("/")
            by_folder.setdefault(folder or ".", []).append(name[:-3])
        touched = "; ".join("%s: %s" % (k, ", ".join(v[:6]) + (" (+%d)" % (len(v) - 6) if len(v) > 6 else ""))
                            for k, v in by_folder.items())
        lines.append("- %s · %s · `%s`%s" % (date, subject, sha, (" · " + touched) if touched else ""))
    older = ""
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "--date=format:%Y-%m", "--format=%ad",
                            "--skip", str(limit)], capture_output=True, text=True, timeout=30)
        months = collections.Counter(r.stdout.split()) if r.returncode == 0 else {}
        if months:
            older = "\n## Older\n\n" + "\n".join("- %s: %d commit(s)" % (m, c) for m, c in sorted(months.items(), reverse=True)) + "\n"
    except Exception:
        pass
    body = "\n".join(head + (lines or ["_No commits yet._"])) + "\n" + older
    (root / "_meta" / "Changelog.md").write_text(body)


CLASS_METHOD = re.compile(r"\b([A-Z][A-Za-z0-9_]+)::([a-zA-Z_][A-Za-z0-9_]*)")
DEF_WORDS = ("function", "def", "fn", "func", "sub", "method", "public", "private", "protected", "static")


def _git(args, cwd):
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True, timeout=60, cwd=cwd)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def attention_signals(root, idx, meta_all):
    """Signals that say a note needs a look. Thresholds from vault.json `tidy`.
    Returns [(signal, stem, detail)] with the strongest first."""
    tidy = vaultlib.CONFIG.get("tidy") or vaultlib.DEFAULT_CONFIG["tidy"]
    max_words = int(tidy.get("max_words") or 4000)
    max_gotchas = int(tidy.get("max_gotchas") or 20)
    stale_days = int(tidy.get("stale_days") or 60)
    churn_min = int(tidy.get("churn_commits") or 5)
    today = datetime.date.today()
    checkouts = list(vaultlib.repo_paths(vaultlib.CONFIG, root).values())

    # which notes own which paths (the hooks' reverse index, reversed again)
    owned = collections.defaultdict(set)
    for path, stems in idx["paths"].items():
        for s in stems:
            owned[s].add(path)

    # one git log per checkout covers every note's churn window
    since = today - datetime.timedelta(days=365)
    churn = collections.defaultdict(set)   # path -> {(date, sha)}
    for c in checkouts:
        out = _git(["log", "--since", since.isoformat(), "--name-only",
                    "--format=%x1e%h %ad", "--date=short"], c)
        for block in out.split("\x1e"):
            lines = [l for l in block.splitlines() if l.strip()]
            if not lines or " " not in lines[0]:
                continue
            sha, date = lines[0].split(" ", 1)
            for f in lines[1:]:
                churn[f.strip()].add((date, sha))
    # files that exist somewhere (working tree, worktrees, committed trees) for rot checks
    basenames = collections.defaultdict(list)
    tracked = set()
    for c in checkouts:
        for f in _git(["ls-files"], c).splitlines():
            tracked.add(f)
            basenames[f.rsplit("/", 1)[-1].split(".", 1)[0]].append(os.path.join(c, f))

    def exists_anywhere(path):
        if not checkouts:
            return True
        if path in tracked:
            return True
        for c in checkouts:
            if os.path.exists(os.path.join(c, path)):
                return True
            for line in _git(["worktree", "list", "--porcelain"], c).splitlines():
                if line.startswith("worktree ") and os.path.exists(os.path.join(line[9:], path)):
                    return True
        return False

    items = []
    for stem, note in idx["notes"].items():
        if note.get("type") in ("", "meta", "release"):
            continue
        words, gotchas = int(note.get("words") or 0), int(note.get("gotchas") or 0)
        if words > max_words or gotchas > max_gotchas:
            bits = []
            if words > max_words:
                bits.append("%d words" % words)
            if gotchas > max_gotchas:
                bits.append("%d gotchas" % gotchas)
            items.append(("consolidate", stem, ", ".join(bits)))
        try:
            updated = datetime.date.fromisoformat(note.get("updated") or "")
        except ValueError:
            updated = None
        touches = set()
        for pth in owned.get(stem, ()):
            for date, sha in churn.get(pth, ()):
                if updated is None or date > updated.isoformat():
                    touches.add(sha)
        if updated and (today - updated).days > stale_days and len(touches) >= churn_min:
            items.append(("re-verify", stem, "updated %s, %d commit(s) touched its files since"
                          % (updated.isoformat(), len(touches))))
        if note.get("depth") == "stub" and len(touches) >= churn_min:
            items.append(("promote", stem, "stub, but %d commit(s) touched its files" % len(touches)))
        if checkouts:
            gone = [c for c in note.get("claims", []) if not exists_anywhere(c)]
            if gone:
                items.append(("path rot", stem, "%s no longer exist%s" % (
                    ", ".join("`%s`" % g for g in gone[:3]) + (" (+%d)" % (len(gone) - 3) if len(gone) > 3 else ""),
                    "s" if len(gone) == 1 else "")))
    # link rot: a reason naming Class::method that no tracked file defines
    if checkouts:
        seen = {}
        for e in idx["links"]:
            for cls, meth in CLASS_METHOD.findall(e.get("reason") or ""):
                key = (cls, meth)
                if key in seen:
                    continue
                files = basenames.get(cls, [])
                found = False
                for f in files[:5]:
                    try:
                        body = open(f, encoding="utf-8", errors="replace").read()
                    except OSError:
                        continue
                    if re.search(r"\b%s\s*\(" % re.escape(meth), body) or \
                            re.search(r"\b(?:%s)\s+%s\b" % ("|".join(DEF_WORDS), re.escape(meth)), body):
                        found = True
                        break
                seen[key] = (found, bool(files))
            for cls, meth in CLASS_METHOD.findall(e.get("reason") or ""):
                found, has_file = seen[(cls, meth)]
                if not found and e["from"] in idx["notes"]:
                    items.append(("link rot", e["from"], "reason names `%s::%s` but %s"
                                  % (cls, meth, "no file named %s.*" % cls if not has_file
                                     else "no definition of %s was found in %s.*" % (meth, cls))))
    order = {"path rot": 0, "link rot": 1, "re-verify": 2, "consolidate": 3, "promote": 4}
    uniq, out = set(), []
    for sig, stem, detail in sorted(items, key=lambda x: (order.get(x[0], 9), x[1])):
        if (sig, stem, detail) not in uniq:
            uniq.add((sig, stem, detail))
            out.append((sig, stem, detail))
    return out


def write_attention(root, items):
    """Maintenance signals (consolidate / re-verify / promote / path rot / link
    rot) as a note plus _meta/status.json for the session primer."""
    today = datetime.date.today().isoformat()
    lines = ["---", "type: meta", f"updated: {today}", "tags: [meta]", "---", "",
             "# Attention", "",
             "> Regenerated by `vault check --write`. Each line is a note the signals say needs a look;",
             "> `/vault:tidy` works the list. Don't hand-edit.", ""]
    if not items:
        lines.append("_Nothing needs attention._")
    else:
        for signal, stem, detail in items:
            lines.append("- **%s** [[%s]] — %s" % (signal, stem, detail))
    (root / "_meta" / "Attention.md").write_text("\n".join(lines) + "\n")
    try:
        (root / "_meta" / "status.json").write_text(json.dumps({
            "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "attention": {"count": len(items),
                          "top": ["%s: %s" % (stem, detail) for _s, stem, detail in items[:3]]},
        }) + "\n")
    except OSError:
        pass


def write_coverage(root, meta, mods, full, stub, total):
    by = {p.stem: meta[p] for p in mods}
    lines = [
        "---",
        "type: meta",
        f"updated: {datetime.date.today().isoformat()}",
        "tags: [meta]",
        "---",
        "",
        "# Coverage",
        "",
        "> Regenerated by `vault check --write`. Don't hand-edit;",
        "> change a note's `depth:` field instead.",
        "",
        f"**{len(full)} of {len(mods)} module notes are `full`.** {total} notes in the vault.",
        "",
        "A `stub` is a real note with real paths and real links — just thin. It gets",
        "promoted the first time we work on that module. See [[How to update]].",
        "",
        "## Full",
        "",
    ]
    for n in full:
        lines.append(f"- [[{n}]] — {by[n].get('domain', '')}")
    lines += ["", "## Stub — promote on next touch", ""]
    for n in stub:
        status = by[n].get("status", "")
        flag = "  *(deprecated)*" if status == "deprecated" else ""
        lines.append(f"- [[{n}]] — {by[n].get('domain', '')}{flag}")
    lines.append("")
    (root / "_meta" / "Coverage.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
