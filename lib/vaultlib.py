#!/usr/bin/env python3
"""Shared vault parser, index builder and vault resolver.

Used by check.py (validation), find.py (retrieval CLI), sync.py (catch-up
report) and hooks/* (Claude Code hooks). Stdlib only, Python 3.9 compatible:
this runs on the system python3 of every machine that has a vault.

A vault is a folder of markdown notes with `_meta/vault.json` describing the
repos it covers. `init()` finds the vault for the current project (explicit
path, VAULT_ROOT env, the folder we are in, or the registry ~/.claude/vaults
matched against the project's git remote or path) and loads its config into
the module globals below.

The index (_meta/index.json) is a generated artifact and is gitignored on
purpose: the Stop hook goes quiet when the vault working tree is dirty, and a
tracked auto-rebuilt index would keep it dirty forever.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

VAULT_ROOT = None      # set by init()
INDEX_PATH = None
CONFIG = {}            # _meta/vault.json merged over DEFAULT_CONFIG
MATCHED_REPO = None    # (key, entry) of the repo entry that matched the project
PROJECT_ROOT = None    # the matched checkout's top level, when known
STATE_PREFIX = "claude-vault-"
SKIP_DIRS = {"_templates", ".obsidian", ".git"}
SCHEMA_VERSION = 2
REGISTRY = Path(os.environ.get("CLAUDE_VAULTS_REGISTRY") or Path.home() / ".claude" / "vaults")

DEFAULT_CONFIG = {
    "name": "",
    "repos": {},
    "generic_dirs": [],
    "path_roots": [],
    "noise_files": [],
    "stop_window_hours": 6,
    "tidy": {"max_words": 4000, "max_gotchas": 20, "stale_days": 60, "churn_commits": 5},
}

# Path classification -----------------------------------------------------------
# Top-level directories that count as code roots. init() extends this set with
# `path_roots` from vault.json and with the real top-level directories of every
# repo the vault covers, so any layout works without configuration.
DEFAULT_PATH_ROOTS = {
    "app", "apps", "src", "lib", "libs", "pkg", "cmd", "internal", "packages",
    "routes", "resources", "database", "db", "config", "tests", "test", "spec",
    "public", "docs", "components", "pages", "api", "server", "client", "web",
    "services", "domain", "core", "modules", "features", "scripts", "migrations",
    "bootstrap", "lang", "changelog", "include", "crates", "plugins",
}
PATH_ROOTS = set(DEFAULT_PATH_ROOTS)
KNOWN_EXTS = (
    ".php", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".vue", ".svelte",
    ".astro", ".py", ".rb", ".go", ".rs", ".java", ".kt", ".kts", ".swift",
    ".cs", ".dart", ".ex", ".exs", ".erl", ".scala", ".clj", ".c", ".cc",
    ".cpp", ".h", ".hpp", ".m", ".mm", ".lua", ".r", ".jl", ".pl", ".sh",
    ".sql", ".proto", ".graphql", ".gql", ".tf", ".html", ".css", ".scss",
    ".sass", ".less", ".md", ".json", ".yml", ".yaml", ".toml", ".xml", ".env",
    ".canvas", ".blade.php", ".erb", ".twig", ".prisma",
)
# Container directories that hold EVERY module's files. A note citing one of
# these (a template row left unfilled, an "all commands live in ..." remark)
# must never become the prefix-owner of everything beneath it, or the pre-edit
# hook would point at the wrong note for hundreds of files. vault.json
# `generic_dirs` extends this list; check.py reports such claims.
DEFAULT_GENERIC_DIRS = {
    "app/Http", "app/Http/Controllers", "app/Http/Requests", "app/Http/Resources",
    "app/Http/Middleware", "app/Services", "app/Models", "app/Jobs", "app/Events",
    "app/Listeners", "app/Console", "app/Console/Commands", "app/Enums",
    "resources/views", "resources/js", "database/migrations", "database/seeders",
    "tests/Feature", "tests/Unit", "src/components", "src/hooks", "src/utils",
    "src/lib", "src/services", "src/pages", "src/api", "lib/services", "pkg",
    "internal", "cmd", "crates",
}
GENERIC_DIRS = set(DEFAULT_GENERIC_DIRS)
# ( ) and [ ] are legal path characters in some routers (route groups such as
# app/(auth)/ and dynamic segments such as [slug]/).
PATHISH = re.compile(r"^[A-Za-z0-9_.\-/()\[\]]+$")
CLASSISH = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
LINE_ANCHOR = re.compile(r":\d+(?:-\d+)?$")
INLINE_SPAN = re.compile(r"`([^`\n]+)`")
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
WHERE_SECTION = re.compile(r"^## Where it lives\n(.*?)(?=^## |\Z)", re.S | re.M)
SEE_IDIOM = re.compile(r"[Ss]ee \[\[([^\]|#]+)[^\]]*\]\]\s*—\s*([^\n]+)")

# Tokens ignored when matching note names against free text.
STOPWORDS = {"and", "to", "the", "a", "an", "of", "in", "on", "for", "vs",
             "is", "are", "it", "its", "we", "not", "by", "with"}


# --- primitives shared with check.py -------------------------------------------

def iter_notes(root=None):
    root = Path(root or VAULT_ROOT)
    for p in root.rglob("*.md"):
        if not SKIP_DIRS & set(p.parts):
            yield p


def strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def strip_fences(text):
    return re.sub(r"```.*?```", "", text, flags=re.S)


def frontmatter(text):
    """Naive flat `key: value` parser — the vault's frontmatter is deliberately
    flat one-liners; nested YAML would parse wrong here AND in Obsidian queries."""
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def parse_inline_list(value):
    """`[a, b c, d]` -> ["a", "b c", "d"]; bare non-empty scalar -> [scalar]."""
    if value is None:
        return []
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        items = []
        for part in inner.split(","):
            part = part.strip().strip("'\"").strip()
            if part:
                items.append(part)
        return items
    return [value]


# --- extraction helpers ---------------------------------------------------------

def normalize_path(span):
    """Code span -> (kind, value) where kind in {path, dir, basename, class, skip}."""
    s = LINE_ANCHOR.sub("", span.strip())
    if not s:
        return ("skip", s)
    if "/" in s:
        if not PATHISH.match(s):
            return ("skip", s)
        is_dir = s.endswith("/")
        while s.startswith("./"):
            s = s[2:]
        s = s.rstrip("/")
        if not s:
            return ("skip", s)
        return ("dir" if is_dir else "path", s)
    if s.endswith(KNOWN_EXTS) and PATHISH.match(s):
        return ("basename", s)
    if CLASSISH.match(s):
        return ("class", s)
    return ("skip", s)


def body_path_ok(path):
    first = path.split("/", 1)[0]
    return first in PATH_ROOTS or path.endswith(KNOWN_EXTS)


def strip_ext(basename):
    for ext in (".blade.php",) + KNOWN_EXTS:
        if basename.endswith(ext):
            return basename[: -len(ext)]
    return basename


def count_bullets(text, heading):
    m = re.search(r"^## %s\s*\n(.*?)(?=^## |\Z)" % re.escape(heading), text, re.S | re.M)
    if not m:
        return 0
    return sum(1 for l in m.group(1).splitlines() if l.lstrip().startswith("- "))


def one_liner(text):
    m = re.search(r"^## What it is\s*\n+(.+?)(?=\n\s*\n|\n#|\Z)", text, re.S | re.M)
    para = m.group(1) if m else None
    if para is None:
        body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        for line in body.splitlines():
            t = line.strip()
            if not t or t.startswith("#") or t.startswith("|") or t.startswith("!["):
                continue
            if t.startswith(">"):
                t = t.lstrip(">").strip()
                if not t:
                    continue
            para = t
            break
    if not para:
        return ""
    para = " ".join(para.split())
    para = re.sub(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]", r"\1", para)
    para = para.replace("**", "").replace("*", "")
    m2 = re.match(r"(.+?\.)\s", para + " ")
    sentence = m2.group(1) if m2 else para
    return sentence[:240]


def trim(text, n):
    """Cut at a word boundary with an ellipsis — no mid-word chops in hints."""
    if text is None or len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return (cut or text[:n]) + "…"


def tokenize(text):
    """Unicode-aware: any script tokenizes; underscores split like punctuation."""
    return [t for t in re.split(r"[\W_]+", text.casefold()) if t]


def significant_tokens(name):
    toks = [t for t in tokenize(name) if t not in STOPWORDS]
    # fold trailing plural s on longer tokens so "tickets" matches "ticket"
    return [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in toks]


# --- index build ----------------------------------------------------------------

def build_index(root=None):
    root = Path(root or VAULT_ROOT)
    files = sorted(iter_notes(root))
    texts = {p: p.read_text() for p in files}
    metas = {p: frontmatter(texts[p]) for p in files}

    # Heuristic paths (a bare basename qualified with its row's directory, a
    # path-shaped span in prose) are only kept when they exist in a known
    # checkout. Explicit Where-it-lives paths are the author's claim and are
    # always kept; check.py reports the ones that no longer exist.
    checkouts = list(repo_paths(CONFIG, root).values()) if CONFIG else []
    refs = {}  # checkout -> refs whose trees also count (the production line)
    try:
        state = json.loads((root / "_meta" / "sync-state.json").read_text())
        for tgt in state.get("targets", []):
            pth = os.path.expanduser(tgt.get("path") or "")
            if pth and os.path.isdir(pth):
                if pth not in checkouts:
                    checkouts.append(pth)
                if tgt.get("ref"):
                    refs.setdefault(pth, []).append(tgt["ref"])
    except (OSError, ValueError):
        pass
    _known = {}

    def known(c):
        """Paths committed on HEAD / the production ref, and the other worktrees
        of this checkout. Work in progress lives on branches and in worktrees;
        a path must not be dropped just because one checkout lacks it."""
        if c not in _known:
            names, wts = set(), []
            for ref in ["HEAD"] + refs.get(c, []):
                out = _git(["ls-tree", "-r", "--name-only", ref], c)
                if out:
                    names.update(out.splitlines())
            out = _git(["worktree", "list", "--porcelain"], c) or ""
            for line in out.splitlines():
                if line.startswith("worktree ") and os.path.realpath(line[9:]) != os.path.realpath(c):
                    wts.append(line[9:])
            _known[c] = (names, wts)
        return _known[c]

    def plausible(path):
        if not checkouts:
            return True
        for c in checkouts:
            if os.path.exists(os.path.join(c, path)):
                return True
        for c in checkouts:
            names, wts = known(c)
            if path in names or any(os.path.exists(os.path.join(w, path)) for w in wts):
                return True
        return False

    stems = {p.stem for p in files}
    alias_map = {}   # lowercased alias -> canonical stem
    alias_exact = {}  # exact alias -> canonical stem (link resolution)
    for p in files:
        for a in parse_inline_list(metas[p].get("aliases")):
            alias_map[a.lower()] = p.stem
            alias_exact[a] = p.stem

    def resolve(target):
        target = target.strip()
        if target in stems:
            return target
        if target in alias_exact:
            return alias_exact[target]
        return alias_map.get(target.lower())

    notes = {}
    paths = {}      # normalized repo-relative path -> set(stems)
    dirs = {}       # directory (from explicit `dir/` spans) -> set(stems)
    classes = {}    # bare class / basename stem -> set(stems)
    global_basenames = {}  # basename -> set(qualified paths) for prose resolution
    edges = []
    edge_seen = set()

    def add(mapping, key, stem):
        mapping.setdefault(key, set()).add(stem)

    for p in files:
        text = texts[p]
        fm = metas[p]
        stem = p.stem
        rel = p.relative_to(root).as_posix()
        # _meta notes cite code paths as writing EXAMPLES — never as ownership.
        is_meta_note = rel.startswith("_meta/")

        # --- Where it lives table: the curated path/class source
        local_base = {}  # basename -> qualified path within this note
        claims = set()   # the author's explicit paths (check.py reports the ones that rot)
        for section in [] if is_meta_note else WHERE_SECTION.findall(text):
            for line in section.splitlines():
                if not line.lstrip().startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if not cells or cells[0] in ("Surface", "") and len(cells) < 2:
                    continue
                if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                    continue
                current_dir = None
                for cell in cells[1:]:
                    for span in INLINE_SPAN.findall(cell):
                        kind, val = normalize_path(span)
                        if kind in ("path", "dir"):
                            if kind == "dir" and val in GENERIC_DIRS:
                                continue
                            claims.add(val)
                            add(paths, val, stem)
                            if kind == "dir" and not ("/" not in val and val in PATH_ROOTS):
                                add(dirs, val, stem)
                            base = val.rsplit("/", 1)[-1]
                            if base.endswith(KNOWN_EXTS):
                                local_base[base] = val
                                add(global_basenames, base, val)
                                cls = strip_ext(base)
                                if CLASSISH.match(cls):
                                    add(classes, cls, stem)
                            current_dir = val.rsplit("/", 1)[0] if "/" in val else None
                        elif kind == "basename":
                            if current_dir and plausible(current_dir + "/" + val):
                                q = current_dir + "/" + val
                                add(paths, q, stem)
                                local_base[val] = q
                                add(global_basenames, val, q)
                            cls = strip_ext(val)
                            if CLASSISH.match(cls):
                                add(classes, cls, stem)
                        elif kind == "class":
                            add(classes, val, stem)

        # --- body code spans (outside fenced blocks): secondary path source
        for span in [] if is_meta_note else INLINE_SPAN.findall(strip_fences(text)):
            kind, val = normalize_path(span)
            if kind in ("path", "dir"):
                if kind == "dir" and val in GENERIC_DIRS:
                    continue
                if body_path_ok(val) and plausible(val):
                    add(paths, val, stem)
                    if kind == "dir" and not ("/" not in val and val in PATH_ROOTS):
                        add(dirs, val, stem)
            elif kind == "basename":
                q = local_base.get(val)
                if q is None:
                    cands = global_basenames.get(val, set())
                    q = next(iter(cands)) if len(cands) == 1 else None
                if q and plausible(q):
                    add(paths, q, stem)

        # --- link edges: reasoned bullets (any section) + the See-idiom
        # Links are detected with inline code spans removed (a backticked
        # [[link]] is not a link — same rule as check.py); the reason text
        # keeps span CONTENT, only the backticks go.
        stripped = strip_fences(text)
        current_section = None
        for line in stripped.splitlines():
            if line.startswith("## "):
                current_section = line[3:].strip()
                continue
            t = line.strip()
            t_nospan = re.sub(r"`[^`\n]*`", "", t)
            t_keep = t.replace("`", "")
            if t.startswith("- ") and "[[" in t_nospan:
                targets = WIKILINK.findall(t_nospan)
                reason = None
                if "—" in t_keep:
                    reason = t_keep.split("—", 1)[1].strip().rstrip(".") or None
                for target in targets:
                    to = resolve(target)
                    if not to or to == stem:
                        continue
                    key = (stem, to, reason)
                    if key not in edge_seen:
                        edge_seen.add(key)
                        edges.append({"from": stem, "to": to, "reason": reason,
                                      "section": current_section})
            else:
                for m in SEE_IDIOM.finditer(t_keep):
                    to = resolve(m.group(1))
                    if not to or to == stem:
                        continue
                    reason = m.group(2).strip().rstrip(".")[:200] or None
                    key = (stem, to, reason)
                    if key not in edge_seen:
                        edge_seen.add(key)
                        edges.append({"from": stem, "to": to, "reason": reason,
                                      "section": current_section})

        notes[stem] = {
            "path": rel,
            "folder": rel.split("/", 1)[0] if "/" in rel else "",
            "type": fm.get("type", ""),
            "status": fm.get("status", ""),
            "depth": fm.get("depth", ""),
            "repo": fm.get("repo", ""),
            "domain": fm.get("domain", ""),
            "updated": fm.get("updated", ""),
            "aliases": parse_inline_list(fm.get("aliases")),
            "tags": parse_inline_list(fm.get("tags")),
            "flags": parse_inline_list(fm.get("flags")),
            "summary": one_liner(text),
            "words": len(text.split()),
            "gotchas": count_bullets(text, "Gotchas"),
            "claims": sorted(claims),
            "inbound": 0,
        }

    for e in edges:
        if e["to"] in notes:
            notes[e["to"]]["inbound"] += 1

    newest = max((p.stat().st_mtime for p in files), default=0.0)
    return {
        "schema_version": SCHEMA_VERSION,
        "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "built_at_mtime": newest,
        "note_count": len(files),
        "notes": notes,
        "aliases": alias_map,
        "paths": {k: sorted(v) for k, v in sorted(paths.items())},
        "dirs": {k: sorted(v) for k, v in sorted(dirs.items())},
        "classes": {k: sorted(v) for k, v in sorted(classes.items())},
        "links": edges,
    }


def write_index(idx, root=None):
    root = Path(root or VAULT_ROOT)
    target = root / "_meta" / "index.json"
    try:
        fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=".index.", suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(idx, f, ensure_ascii=False)
        os.replace(tmp, str(target))
    except OSError:
        pass  # read-only fs etc. — callers still have the in-memory index


def load_index(root=None):
    """Load index.json; rebuild automatically when any note is newer or the
    note count changed. Always returns a usable index."""
    root = Path(root or VAULT_ROOT)
    target = root / "_meta" / "index.json"
    files = list(iter_notes(root))
    if not files:
        raise RuntimeError("no notes found under %s" % root)
    newest = max(p.stat().st_mtime for p in files)
    if target.exists():
        try:
            idx = json.loads(target.read_text())
            if (idx.get("schema_version") == SCHEMA_VERSION
                    and idx.get("built_at_mtime", 0) >= newest
                    and idx.get("note_count") == len(files)):
                return idx
        except (ValueError, OSError):
            pass
    idx = build_index(root)
    write_index(idx, root)
    return idx


# --- vault resolution + config --------------------------------------------------

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "vault").lower()).strip("-") or "vault"


def _git(args, cwd):
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True, timeout=5, cwd=cwd)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def project_of(cwd):
    """(top-level dir, origin url) of the git checkout containing cwd, or (None, None)."""
    top = _git(["rev-parse", "--show-toplevel"], cwd) if cwd and os.path.isdir(cwd) else None
    if not top:
        return None, None
    return top, (_git(["remote", "get-url", "origin"], top) or "")


def read_registry():
    """Registered vault paths: ~/.claude/vaults (one per line, # comments) plus
    the CLAUDE_VAULTS env (os.pathsep-separated)."""
    out = []
    try:
        for line in REGISTRY.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    except OSError:
        pass
    for extra in (os.environ.get("CLAUDE_VAULTS") or "").split(os.pathsep):
        if extra.strip():
            out.append(extra.strip())
    seen, uniq = set(), []
    for v in out:
        p = Path(os.path.expanduser(v))
        if p not in seen and (p / "_meta" / "vault.json").is_file():
            seen.add(p)
            uniq.append(p)
    return uniq


def read_config(root):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        data = json.loads((Path(root) / "_meta" / "vault.json").read_text())
    except (OSError, ValueError):
        data = {}
    for k, v in data.items():
        if k == "tidy" and isinstance(v, dict):
            cfg["tidy"].update(v)
        else:
            cfg[k] = v
    return cfg


def normalize_remote(url):
    """`git@host:owner/name.git`, `ssh://git@host/owner/name`, `https://host/owner/name.git`
    -> `host/owner/name`, so a vault.json `remote` matches whichever form a clone uses."""
    u = (url or "").strip()
    u = re.sub(r"^[a-z+]+://", "", u)          # scheme
    u = re.sub(r"^[^@/]+@", "", u)             # user@
    u = u.replace(":", "/", 1) if re.match(r"^[^/]+:", u) else u
    u = re.sub(r"\.git/?$", "", u)
    return u.lower()


def match_repo(cfg, top, origin, cwd=None):
    """The repo entry of `cfg` that covers this checkout: (key, entry, score) or None.
    Remote substring match or local path match; longest match wins; an entry
    with `root` (monorepo sub-app) only matches when cwd is inside it."""
    best = None
    top_real = os.path.realpath(top) if top else None
    for key, entry in (cfg.get("repos") or {}).items():
        if not isinstance(entry, dict):
            continue
        score = 0
        remote = entry.get("remote")
        path = entry.get("path")
        if remote and origin and normalize_remote(remote) in normalize_remote(origin):
            score = len(remote)
        elif path and top_real:
            p = os.path.realpath(os.path.expanduser(path))
            if top_real == p or top_real.startswith(p + os.sep):
                score = 10000 + len(p)
        if not score:
            continue
        sub = entry.get("root")
        if sub:
            inside = os.path.join(top_real or "", sub.strip("/"))
            here = os.path.realpath(cwd or top or "")
            if not (here == inside or here.startswith(inside + os.sep)):
                continue
            score += len(sub)
        if best is None or score > best[2]:
            best = (key, entry, score)
    return best


def resolve_vault(cwd=None, explicit=None):
    """Find the vault for this context. Returns (root, cfg, matched_repo, top) or None."""
    cwd = cwd or os.getcwd()
    top, origin = project_of(cwd)
    root = explicit or os.environ.get("VAULT_ROOT")
    if root:
        root = Path(os.path.expanduser(root)).resolve()
        cfg = read_config(root)
        return root, cfg, match_repo(cfg, top, origin, cwd), top
    # inside a vault?
    p = Path(cwd).resolve()
    for cand in (p, *p.parents):
        if (cand / "_meta" / "vault.json").is_file():
            cfg = read_config(cand)
            return cand, cfg, match_repo(cfg, top, origin, cwd), top
    # registry match on this checkout
    if not top:
        return None
    best = None
    for vault in read_registry():
        cfg = read_config(vault)
        m = match_repo(cfg, top, origin, cwd)
        if m and (best is None or m[2] > best[2][2]):
            best = (vault, cfg, m)
    if best:
        return best[0], best[1], best[2], top
    return None


def repo_paths(cfg, root):
    """Local checkout paths known for this vault's repos: vault.json `path`
    entries plus sync-state targets. Only paths that exist on this machine."""
    out = {}
    for key, entry in (cfg.get("repos") or {}).items():
        p = entry.get("path") if isinstance(entry, dict) else None
        if p and os.path.isdir(os.path.expanduser(p)):
            out[key] = os.path.expanduser(p)
    try:
        state = json.loads((Path(root) / "_meta" / "sync-state.json").read_text())
        for t in state.get("targets", []):
            if t.get("path") and os.path.isdir(os.path.expanduser(t["path"])):
                out.setdefault(t.get("name", t["path"]), os.path.expanduser(t["path"]))
    except (OSError, ValueError):
        pass
    if PROJECT_ROOT and MATCHED_REPO:
        out.setdefault(MATCHED_REPO[0], PROJECT_ROOT)
    return out


_SKIP_TOP = {"node_modules", "vendor", "dist", "build", "target", ".git", "storage", "tmp", "coverage"}


def top_level_dirs(repo):
    try:
        return {d for d in os.listdir(repo)
                if not d.startswith(".") and d not in _SKIP_TOP and os.path.isdir(os.path.join(repo, d))}
    except OSError:
        return set()


def init(root=None, cwd=None):
    """Resolve the vault and load its config into the module globals.
    Returns the vault root, or None when no vault covers this project."""
    global VAULT_ROOT, INDEX_PATH, CONFIG, MATCHED_REPO, PROJECT_ROOT
    global PATH_ROOTS, GENERIC_DIRS, STATE_PREFIX
    found = resolve_vault(cwd=cwd, explicit=root)
    if not found:
        return None
    VAULT_ROOT, CONFIG, m, PROJECT_ROOT = found
    MATCHED_REPO = (m[0], m[1]) if m else None
    INDEX_PATH = VAULT_ROOT / "_meta" / "index.json"
    STATE_PREFIX = "claude-vault-%s-" % slug(CONFIG.get("name") or VAULT_ROOT.name)
    GENERIC_DIRS = set(DEFAULT_GENERIC_DIRS) | set(CONFIG.get("generic_dirs") or [])
    roots = set(DEFAULT_PATH_ROOTS) | set(CONFIG.get("path_roots") or [])
    for repo in repo_paths(CONFIG, VAULT_ROOT).values():
        roots |= top_level_dirs(repo)
    PATH_ROOTS = roots
    return VAULT_ROOT


def require(root=None, cwd=None):
    """init() or exit with a one-line explanation (for the CLIs)."""
    if init(root=root, cwd=cwd):
        return VAULT_ROOT
    sys.exit("no vault covers this project. Run from inside a vault or a covered "
             "checkout, set VAULT_ROOT, or create one: vault init <path> --repo <checkout>")


# --- matching (shared by find.py and the hooks) ---------------------------------

def phrase(text):
    """Normalized token phrase: 'Sign-In' -> 'sign in'."""
    return " ".join(tokenize(text))


def contains_phrase(lowered, raw):
    """Whole-token phrase containment against an already-normalized text."""
    p = phrase(raw)
    return bool(p) and (" %s " % p) in (" %s " % lowered)


def needs_phrase(raw):
    """A multi-word name/alias that stopword removal reduces to ONE token
    ('Sign In' -> 'sign') would otherwise match every prompt containing that
    token; such names match only as a contiguous phrase."""
    return len(tokenize(raw)) > 1 and len(significant_tokens(raw)) == 1


def match_terms(idx, text, tier1_only=False):
    """Match free text against note names/aliases (T1) and tags/domain/flags (T2).

    Long text (>3 tokens, i.e. prose from a prompt) is matched strictly: a
    multi-word note name needs ALL its significant tokens present; short text
    (an explicit query) also accepts partial token overlap, scored.
    Returns [(stem, matched_by, score)] sorted best-first.
    """
    qtokens = set(significant_tokens(text))
    if not qtokens:
        return []
    explicit = len(tokenize(text)) <= 3
    lowered = " ".join(tokenize(text))
    hits = {}

    def record(stem, matched_by, score):
        cur = hits.get(stem)
        if cur is None or score > cur[1]:
            hits[stem] = (matched_by, score)

    for stem, note in idx["notes"].items():
        stoks = significant_tokens(stem)
        if not stoks:
            continue
        overlap = sum(1 for t in stoks if t in qtokens)
        if needs_phrase(stem):
            full = contains_phrase(lowered, stem)
        else:
            full = overlap == len(stoks) and (len(stoks) > 1 or len(stoks[0]) >= 3)
        if full:
            record(stem, "name", 3.0 + len(stoks))
        elif explicit and overlap:
            record(stem, "name-partial", 1.0 + overlap / len(stoks))
        for alias in note.get("aliases", []):
            atoks = significant_tokens(alias)
            if needs_phrase(alias):
                if contains_phrase(lowered, alias):
                    record(stem, "alias:%s" % alias, 3.0 + len(atoks))
                elif explicit and atoks and all(t in qtokens for t in atoks):
                    record(stem, "alias:%s" % alias, 2.0)
            elif atoks and all(t in qtokens for t in atoks):
                record(stem, "alias:%s" % alias, 3.0 + len(atoks))
            elif len(alias) >= 3 and contains_phrase(lowered, alias):
                record(stem, "alias:%s" % alias, 2.5)
        for flag in note.get("flags", []):
            # `lowered` is tokenized (underscores become spaces), so compare the
            # flag the same way; a raw FEATURE_X_ENABLED would never match.
            if flag and contains_phrase(lowered, flag):
                record(stem, "flag:%s" % flag, 4.0)

    if not tier1_only and (explicit or not hits):
        for stem, note in idx["notes"].items():
            if stem in hits:
                continue
            hay = set()
            for tag in note.get("tags", []):
                hay.update(significant_tokens(tag.split("/")[-1]))
            hay.update(significant_tokens(note.get("domain", "")))
            overlap = qtokens & hay
            if overlap and explicit:
                record(stem, "tag/domain:%s" % ",".join(sorted(overlap)), 0.5 + 0.1 * len(overlap))

    ranked = sorted(
        hits.items(),
        key=lambda kv: (-kv[1][1], -idx["notes"][kv[0]].get("inbound", 0), kv[0]),
    )
    return [(stem, mb, score) for stem, (mb, score) in ranked]


def _relativize(path, cwd=None, project_dir=None):
    """Absolute or relative file path -> repo-relative posix path (best effort)."""
    p = path.replace("\\", "/")
    if not p.startswith("/"):
        # strip "./" prefixes only — lstrip("./") also ate the dot of
        # ".claude/..." and the dots of "../" segments.
        while p.startswith("./"):
            p = p[2:]
        return p
    roots = []
    if project_dir:
        roots.append(project_dir.rstrip("/"))
    if cwd:
        roots.append(cwd.rstrip("/"))
    # walk up from the file looking for a repo root
    parent = Path(p).parent
    while parent != parent.parent:
        if (parent / ".git").exists():
            roots.append(str(parent))
            break
        parent = parent.parent
    for r in roots:
        if p.startswith(r + "/"):
            return p[len(r) + 1:]
    return p.lstrip("/")


# A path owned by more notes than this is weak evidence: a shared routes file
# or a global stylesheet owned by a dozen notes tells you nothing, while a file
# a handful of notes share in lock-step is exactly the hint worth surfacing.
SHARED_PATH_OWNERS = 6
# Basenames too generic to identify a module (every skill/readme shares them).
GENERIC_STEMS = {"SKILL", "README", "CLAUDE", "LICENSE", "TODO", "CHANGELOG", "Controller", "Service", "Model"}


def match_paths(idx, file_paths, cwd=None, project_dir=None):
    """Map file paths to owning notes. Returns [(stem, via, priority)] sorted,
    priority 0 = specific exact path, 1 = dir prefix, 2 = class/basename,
    3 = shared path (owned by many notes)."""
    results = {}

    def record(stem, via, prio):
        cur = results.get(stem)
        if cur is None or prio < cur[1]:
            results[stem] = (via, prio)

    for raw in file_paths:
        rel = LINE_ANCHOR.sub("", _relativize(raw, cwd, project_dir))
        owners = idx["paths"].get(rel)
        if owners:
            prio = 3 if len(owners) > SHARED_PATH_OWNERS else 0
            for s in owners:
                record(s, rel, prio)
            if prio == 0:
                continue
        # Fallbacks (dir prefix / basename / class) only apply to recognized
        # code roots — a match on e.g. `.claude/**` or a dotfile would be a
        # coincidence of naming, not ownership.
        parts = rel.split("/")
        if parts[0] not in PATH_ROOTS:
            continue
        matched_dir = False
        for i in range(len(parts) - 1, 0, -1):
            d = "/".join(parts[:i])
            if d in idx["dirs"]:
                d_owners = idx["dirs"][d]
                prio = 3 if len(d_owners) > SHARED_PATH_OWNERS else 1
                for s in d_owners:
                    record(s, d + "/", prio)
                matched_dir = True
                break
        if matched_dir:
            continue
        base = parts[-1]
        cls = strip_ext(base)
        if (cls != base and cls not in GENERIC_STEMS
                and CLASSISH.match(cls) and cls in idx["classes"]):
            for s in idx["classes"][cls]:
                record(s, "class:%s" % cls, 2)

    return sorted(
        ((stem, via, prio) for stem, (via, prio) in results.items()),
        key=lambda t: (t[2], -idx["notes"].get(t[0], {}).get("inbound", 0), t[0]),
    )


def neighbors(idx, stem, limit=6):
    """One-hop edges for a note, reasoned ones first: [(direction, other, reason)]."""
    out = []
    for e in idx["links"]:
        if e["from"] == stem and e["to"] in idx["notes"]:
            out.append(("→", e["to"], e["reason"]))
        elif e["to"] == stem and e["from"] in idx["notes"]:
            out.append(("←", e["from"], e["reason"]))
    seen = set()
    uniq = []
    for d, other, reason in sorted(out, key=lambda t: (t[2] is None, t[0] == "←")):
        if other not in seen:
            seen.add(other)
            uniq.append((d, other, reason))
    return uniq[:limit]
