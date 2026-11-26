#!/usr/bin/env python3
"""vault init: scaffold and register a knowledge vault.

    vault init                       # inside a git checkout: a vault for this repo, all defaults
    vault init --plan                # print what the line above would do, change nothing
    vault init <path> --name NAME --repo <checkout> [--repo ...] [options]
    vault init --clone <url> [<path>] [--repo <checkout> ...] [options]
    vault init --adopt <existing-vault> --name NAME [--repo <checkout> ...] [options]
    vault init --install-cli
    vault init --forget [<vault>]    # stop using a vault here: unregister it, remove our git hooks

With no path, --clone or --adopt, the vault covers the checkout you are in, is
named after its folder, goes to ~/vaults/<name>, and the `vault` launcher is
installed (--no-cli skips that).

Options:
    --repo <checkout>      a local checkout the vault covers (repeatable). Its git
                           remote (or, without one, its path) becomes the routing key.
    --install-cli          copy the `vault` launcher to ~/.local/bin
    --git-hook             install report-only post-merge and pre-push hooks in
                           each checkout (they print how far the vault is behind)
    --backup-remote <url>  add `origin` to the vault and auto-push after each commit
    --no-git               do not `git init` / commit the new vault

A fresh vault gets the scaffold (Home, conventions, templates, Obsidian config,
Bases views), the nine folders, one `8 Repos/<name>.md` stub per checkout,
`_meta/vault.json` (what the hooks route on) and `_meta/sync-state.json`
(cursors for `vault sync`), and is registered in ~/.claude/vaults so the hooks
find it from any covered checkout. Python 3.9, stdlib only.
"""
import datetime
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402

PLUGIN = Path(__file__).resolve().parents[1]
SCAFFOLD = PLUGIN / "scaffold"
FOLDERS = ["1 Domains", "2 Modules", "3 Flows", "4 Integrations", "5 Platform",
           "6 Decisions", "7 Releases", "8 Repos", "9 Glossary"]
GITIGNORE = """# Obsidian per-device UI state
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.DS_Store
.trash/

# Generated search index and status cache (vault check --write). Keep them
# ignored: the Stop reminder goes quiet while the vault is dirty, and a tracked
# auto-rebuilt index would keep it dirty forever.
_meta/index.json
_meta/status.json
__pycache__/
*.pyc
"""
SKIP_TOP = {"node_modules", "vendor", "dist", "build", "target", "storage", "tmp", "coverage",
            "public", "static", "assets", "docs", "doc", "tests", "test", "spec", "__tests__",
            "bin", "scripts", "fixtures", "examples", "example"}


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def has_code(d, depth=2):
    try:
        for root, dirs, files in os.walk(d):
            if root[len(str(d)):].count(os.sep) >= depth:
                dirs[:] = []
            dirs[:] = [x for x in dirs if not x.startswith(".") and x not in SKIP_TOP]
            if any(f.endswith(vaultlib.KNOWN_EXTS) and not f.endswith((".md", ".json", ".yml", ".yaml", ".toml", ".xml", ".env"))
                   for f in files):
                return True
    except OSError:
        pass
    return False


def detect_watched(checkout):
    """Directories worth watching for the Stop reminder: a known layout's set,
    otherwise every top-level directory that holds code."""
    c = Path(checkout)
    exists = lambda *names: [n for n in names if (c / n).is_dir()]  # noqa: E731
    if (c / "artisan").is_file():
        return exists("app", "routes", "resources/views", "database/migrations", "config")
    if any(c.glob("next.config.*")):
        return exists("app", "pages", "components", "src", "lib")
    if (c / "manage.py").is_file() or (c / "Gemfile").is_file() or (c / "go.mod").is_file() \
            or (c / "Cargo.toml").is_file() or (c / "package.json").is_file() or True:
        found = []
        try:
            for d in sorted(os.listdir(c)):
                if d.startswith(".") or d in SKIP_TOP:
                    continue
                if (c / d).is_dir() and has_code(c / d):
                    found.append(d)
        except OSError:
            pass
        return found or ["src"]


def detect_repo(checkout):
    c = Path(os.path.expanduser(checkout)).resolve()
    if not git(c, "rev-parse", "--show-toplevel"):
        sys.exit("not a git checkout: %s" % c)
    key = c.name
    origin = git(c, "remote", "get-url", "origin")
    entry = {}
    if origin:
        entry["remote"] = vaultlib.normalize_remote(origin)
    else:
        entry["path"] = str(c).replace(str(Path.home()), "~", 1)
    entry["watched"] = detect_watched(c)
    head_ref = git(c, "symbolic-ref", "refs/remotes/origin/HEAD")
    if head_ref:
        prod = head_ref.replace("refs/remotes/", "", 1)
    else:
        branch = git(c, "rev-parse", "--abbrev-ref", "HEAD") or "main"
        prod = ("origin/" + branch) if origin and git(c, "rev-parse", "--verify", "-q", "origin/" + branch) else branch
    entry["production_ref"] = prod
    for vlog in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"):
        if (c / vlog).is_file():
            entry["version_log"] = vlog
            break
    head = git(c, "rev-parse", prod) or git(c, "rev-parse", "HEAD")
    return key, entry, str(c), head


def copy_scaffold(dest, name):
    if not SCAFFOLD.is_dir():
        return
    for src in SCAFFOLD.rglob("*"):
        rel = src.relative_to(SCAFFOLD)
        target = dest / rel
        if src.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in (".md", ".base", ".canvas", ".json") and src.name != "vault.json":
            text = src.read_text()
            target.write_text(text.replace("{{name}}", name)
                              .replace("{{date}}", datetime.date.today().isoformat()))
        else:
            shutil.copy2(src, target)


def repo_stub(key, entry):
    today = datetime.date.today().isoformat()
    where = entry.get("remote") or entry.get("path") or ""
    return ("---\ntype: repo\nstatus: shipped\ndepth: stub\nrepo: %s\nupdated: %s\ntags: [repo]\n---\n\n"
            "# %s\n\n## What it is\n\n_One or two plain sentences on what this repository is._\n\n"
            "## Where it lives\n\n`%s` — production branch `%s`; the hooks watch `%s`.\n\n"
            "## How it works\n\n_Entry points, how to run it, how it is deployed._\n\n"
            "## Connects to\n\n- [[Home]] — the vault's entry page lists this repo\n\n"
            "## Gotchas\n\n-\n" % (key, today, key, where, entry.get("production_ref", ""),
                                    ", ".join(entry.get("watched") or [])))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def register(path):
    reg = vaultlib.REGISTRY
    line = str(Path(path).resolve())
    try:
        lines = [l.strip() for l in reg.read_text().splitlines()]
    except OSError:
        lines = []
    if line in lines:
        return
    reg.parent.mkdir(parents=True, exist_ok=True)
    with open(reg, "a") as f:
        f.write(line + "\n")
    print("registered in %s" % reg)


def install_cli():
    src = PLUGIN / "bin" / "vault"
    dest = Path.home() / ".local" / "bin" / "vault"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("installed %s" % dest)
    if str(dest.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print("  add it to your PATH:  export PATH=\"$HOME/.local/bin:$PATH\"")


def install_git_hooks(checkouts):
    body = (PLUGIN / "lib" / "git-hooks" / "report.sh").read_text()
    for c in checkouts:
        common = git(c, "rev-parse", "--git-common-dir")
        if not common:
            continue
        hooks = Path(c) / common / "hooks" if not os.path.isabs(common) else Path(common) / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        done = []
        for name in ("post-merge", "pre-push"):
            target = hooks / name
            if target.exists() and "# claude-vault git hook body" not in target.read_text():
                print("  %s: %s exists and is not ours; left alone" % (Path(c).name, name))
                continue
            target.write_text(body)
            target.chmod(target.stat().st_mode | stat.S_IXUSR)
            done.append(name)
        if done:
            print("  %s: %s hook%s installed" % (Path(c).name, " + ".join(done), "s" * (len(done) > 1)))


def backup_remote(vault, url):
    if not git(vault, "remote", "get-url", "origin"):
        subprocess.run(["git", "-C", str(vault), "remote", "add", "origin", url], check=False)
    hooks = vault / "_meta" / "git-hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLUGIN / "lib" / "git-hooks" / "post-commit", hooks / "post-commit")
    (hooks / "post-commit").chmod(0o755)
    subprocess.run(["git", "-C", str(vault), "config", "core.hooksPath", "_meta/git-hooks"], check=False)
    print("backup remote set; every vault commit pushes to %s" % url)


def build_config(name, repos):
    return {
        "name": name,
        "repos": {k: e for k, e, _c, _h in repos},
        "generic_dirs": [],
        "noise_files": [],
        "stop_window_hours": 6,
        "tidy": dict(vaultlib.DEFAULT_CONFIG["tidy"]),
    }


def build_sync_state(repos):
    targets = []
    for key, entry, checkout, head in repos:
        t = {"name": key, "path": checkout, "ref": entry.get("production_ref", "HEAD"), "last": head}
        if entry.get("version_log"):
            t["version_log"] = entry["version_log"]
        targets.append(t)
    return {"targets": targets}


def fresh(path, name, repos, opts):
    dest = Path(os.path.expanduser(path)).resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit("%s exists and is not empty (use --adopt for an existing vault)" % dest)
    dest.mkdir(parents=True, exist_ok=True)
    copy_scaffold(dest, name)
    for f in FOLDERS:
        (dest / f).mkdir(exist_ok=True)
    for key, entry, _c, _h in repos:
        (dest / "8 Repos" / (key + ".md")).write_text(repo_stub(key, entry))
    home = dest / "Home.md"
    if home.exists() and repos:
        # link every repo note from the entry page so none starts as an orphan
        links = ", ".join("[[%s]]" % k for k, _e, _c, _h in repos)
        text = home.read_text()
        marker = "one orientation note per codebase in `8 Repos`."
        home.write_text(text.replace(marker, "one orientation note per codebase in `8 Repos`: %s." % links, 1)
                        if marker in text else text.rstrip("\n") + "\n\n## Repos\n\n%s\n" % links)
    if not (dest / "Home.md").exists():
        (dest / "Home.md").write_text("---\ntype: meta\nupdated: %s\ntags: [meta]\n---\n\n# %s\n\n"
                                      "The world map of %s.\n" % (datetime.date.today().isoformat(), name, name))
    if not (dest / "World.canvas").exists():
        (dest / "World.canvas").write_text('{"nodes":[],"edges":[]}\n')
    if not (dest / ".gitignore").exists():
        (dest / ".gitignore").write_text(GITIGNORE)
    write_json(dest / "_meta" / "vault.json", build_config(name, repos))
    write_json(dest / "_meta" / "sync-state.json", build_sync_state(repos))
    subprocess.run([sys.executable, str(PLUGIN / "lib" / "check.py"), "--vault", str(dest), "--write"],
                   capture_output=True, text=True)
    if not opts["no_git"]:
        subprocess.run(["git", "-C", str(dest), "init", "-q"], check=False)
        subprocess.run(["git", "-C", str(dest), "add", "-A"], check=False)
        subprocess.run(["git", "-C", str(dest), "commit", "-q", "-m", "Start the %s knowledge vault" % name], check=False)
    print("created %s" % dest)
    return dest


def adopt(existing, name, repos):
    dest = Path(os.path.expanduser(existing)).resolve()
    if not dest.is_dir():
        sys.exit("no such folder: %s" % dest)
    cfg_path = dest / "_meta" / "vault.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        cfg.setdefault("repos", {}).update({k: e for k, e, _c, _h in repos})
        if name:
            cfg["name"] = name
    else:
        cfg = build_config(name or dest.name, repos)
    write_json(cfg_path, cfg)
    state_path = dest / "_meta" / "sync-state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text())
        known = {t.get("name") for t in state.get("targets", [])}
        state["targets"] += [t for t in build_sync_state(repos)["targets"] if t["name"] not in known]
    else:
        state = build_sync_state(repos)
    write_json(state_path, state)
    for f in FOLDERS:
        (dest / f).mkdir(exist_ok=True)
    print("adopted %s" % dest)
    return dest


def clone(url, path, repos):
    dest = Path(os.path.expanduser(path or re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1]))).resolve()
    r = subprocess.run(["git", "clone", "-q", url, str(dest)])
    if r.returncode != 0:
        sys.exit("clone failed")
    cfg_path = dest / "_meta" / "vault.json"
    if not cfg_path.exists():
        sys.exit("%s has no _meta/vault.json; it is not a Lightkeeper vault (use --adopt)" % dest)
    if repos:
        adopt(dest, None, repos)
    print("cloned %s" % dest)
    return dest


def parse(argv):
    opts = {"path": None, "name": None, "repos": [], "install_cli": False, "git_hook": False,
            "backup": None, "no_git": False, "clone": None, "adopt": None,
            "plan": False, "no_cli": False, "forget": False}
    it = iter(argv)
    for a in it:
        if a == "--name":
            opts["name"] = next(it, None)
        elif a == "--repo":
            opts["repos"].append(next(it, None))
        elif a == "--install-cli":
            opts["install_cli"] = True
        elif a == "--git-hook":
            opts["git_hook"] = True
        elif a == "--backup-remote":
            opts["backup"] = next(it, None)
        elif a == "--no-git":
            opts["no_git"] = True
        elif a == "--plan":
            opts["plan"] = True
        elif a == "--no-cli":
            opts["no_cli"] = True
        elif a == "--forget":
            opts["forget"] = True
        elif a == "--clone":
            opts["clone"] = next(it, None)
        elif a == "--adopt":
            opts["adopt"] = next(it, None)
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            sys.exit(0)
        elif a.startswith("-"):
            sys.exit("unknown option %s" % a)
        else:
            opts["path"] = a
    return opts


def defaults(opts):
    """Fill path, name and repo from the checkout we are in. Returns an error line or None."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    top, _origin = vaultlib.project_of(cwd)
    if not top and not opts["repos"]:
        return ("not inside a git checkout: run this from the project the vault should cover, "
                "or pass <path> --repo <checkout>")
    if not opts["repos"]:
        found = vaultlib.resolve_vault(cwd=cwd)
        if found and found[2]:
            return "this checkout is already covered by %s (see: vault status)" % found[0]
        opts["repos"] = [top]
    if not opts["name"]:
        opts["name"] = Path(os.path.expanduser(opts["repos"][0])).resolve().name
    opts["path"] = str(Path.home() / "vaults" / vaultlib.slug(opts["name"]))
    if not opts["no_cli"]:
        opts["install_cli"] = True
    return None


def remove_git_hooks(checkouts):
    for c in checkouts:
        common = git(c, "rev-parse", "--git-common-dir")
        if not common:
            continue
        hooks = Path(c) / common / "hooks" if not os.path.isabs(common) else Path(common) / "hooks"
        for name in ("post-merge", "pre-push"):
            target = hooks / name
            try:
                if "# claude-vault git hook body" in target.read_text():
                    target.unlink()
                    print("  %s: %s hook removed" % (Path(c).name, name))
            except OSError:
                pass


def forget(path):
    """Unregister a vault and remove the git hooks we installed. The folder stays."""
    if path:
        dest = Path(os.path.expanduser(path)).resolve()
    else:
        found = vaultlib.resolve_vault(cwd=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        if not found:
            sys.exit("no vault covers this folder; name one: vault init --forget <vault>")
        dest = Path(found[0]).resolve()
    reg = vaultlib.REGISTRY
    try:
        lines = reg.read_text().splitlines()
    except OSError:
        lines = []
    kept = [l for l in lines if not l.strip() or l.strip().startswith("#")
            or Path(os.path.expanduser(l.strip())).resolve() != dest]
    if len(kept) == len(lines):
        print("%s was not registered in %s" % (dest, reg))
    else:
        reg.write_text("\n".join(kept) + ("\n" if kept else ""))
        print("unregistered %s (the hooks no longer use it)" % dest)
    try:
        state = json.loads((dest / "_meta" / "sync-state.json").read_text())
    except (OSError, ValueError):
        state = {}
    remove_git_hooks([os.path.expanduser(t["path"]) for t in state.get("targets", []) if t.get("path")])
    print("the folder is untouched; bring it back with: vault init --adopt %s" % dest)
    return 0


def main(argv):
    opts = parse(argv)
    if opts["forget"]:
        return forget(opts["path"])
    cli_only = opts["install_cli"] and not (opts["repos"] or opts["name"] or opts["git_hook"] or opts["plan"])
    if not (opts["path"] or opts["clone"] or opts["adopt"] or cli_only):
        err = defaults(opts)
        if err:
            print(err)
            return 2
    if opts["plan"]:
        print("would create the vault %s, named \"%s\", covering %s%s" % (
            opts["path"] or opts["adopt"] or opts["clone"], opts["name"] or "",
            ", ".join(str(Path(os.path.expanduser(r)).resolve()) for r in opts["repos"]) or "no repo",
            "; and install the vault command in ~/.local/bin" if opts["install_cli"] else ""))
        return 0
    repos = [detect_repo(r) for r in opts["repos"] if r]
    dest = None
    if opts["clone"]:
        dest = clone(opts["clone"], opts["path"], repos)
    elif opts["adopt"]:
        dest = adopt(opts["adopt"], opts["name"], repos)
    elif opts["path"]:
        if not opts["name"]:
            opts["name"] = Path(opts["path"]).name
        if not repos:
            print("note: no --repo given; the hooks route by repo, so add one later with "
                  "`vault init --adopt <vault> --repo <checkout>`")
        dest = fresh(opts["path"], opts["name"], repos, opts)
    elif not opts["install_cli"]:
        print(__doc__.strip())
        return 2
    if opts["install_cli"]:
        install_cli()
    if dest:
        register(dest)
        if opts["git_hook"] and repos:
            install_git_hooks([c for _k, _e, c, _h in repos])
        if opts["backup"]:
            backup_remote(dest, opts["backup"])
        print("\nnext: seed the first notes with /lightkeeper:seed (the file pointer works as soon "
              "as notes own files, in this session too; the session primer shows from your next "
              "session). To look at the map: open %s in Obsidian (Open folder as vault), or "
              "`vault export --html map.html`. Check the setup any time with `vault doctor`." % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
