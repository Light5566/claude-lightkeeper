#!/usr/bin/env python3
"""vault doctor: is Lightkeeper set up and working here? One screen, a fix beside each problem.

    vault doctor            # check this folder
    vault doctor --vault PATH

Checks Python and git, the plugin, the registry, whether this folder is covered
and by which vault, whether any note owns code yet, whether `vault` is on PATH,
and whether the hooks have run lately. Exits 1 when something needs fixing.
A hook that fails does so silently by design; run a session with
VAULT_HOOK_DEBUG=1 to see its traceback. Stdlib only, Python 3.9.
"""
import glob
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vaultlib  # noqa: E402

PLUGIN = Path(__file__).resolve().parents[1]


def version():
    try:
        return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text()).get("version") or "?"
    except (OSError, ValueError):
        return "?"


def last_hook_run():
    """(seconds ago, runs by hook) of the newest session state for this vault, or None."""
    prefix = os.path.join(os.environ.get("TMPDIR") or "/tmp", vaultlib.STATE_PREFIX)
    files = [p for p in glob.glob(prefix + "*.json") if not p.endswith("-vault.json")]
    if not files:
        return None
    path = max(files, key=os.path.getmtime)
    try:
        runs = json.loads(Path(path).read_text()).get("runs") or {}
    except (OSError, ValueError):
        runs = {}
    return time.time() - os.path.getmtime(path), runs


def main(argv):
    vault_opt = None
    it = iter(argv)
    for a in it:
        if a == "--vault":
            vault_opt = next(it, None)
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
    bad = 0

    def line(ok, text, fix=None):
        nonlocal bad
        if ok:
            print("ok   %s" % text)
        else:
            bad += 1
            print("FIX  %s%s" % (text, ("\n     -> " + fix) if fix else ""))

    line(sys.version_info >= (3, 9), "Python %d.%d" % sys.version_info[:2],
         "Lightkeeper needs Python 3.9 or newer as `python3` on your PATH")
    line(bool(shutil.which("git")), "git", "install git")
    print("ok   plugin %s at %s" % (version(), PLUGIN))

    vaults = vaultlib.read_registry()
    line(bool(vaults), "registry %s lists %d vault(s)" % (vaultlib.REGISTRY, len(vaults)),
         "no vault is registered: run /lightkeeper:init in the project (or: vault init)")

    cwd = os.getcwd()
    root = vaultlib.init(root=vault_opt, cwd=cwd)
    if not root:
        line(False, "no vault covers %s" % cwd,
             "run /lightkeeper:init from inside the project (or: vault init); "
             "a vault that exists already: vault init --adopt <vault> --repo <checkout>")
    else:
        repo = vaultlib.MATCHED_REPO[0] if vaultlib.MATCHED_REPO else None
        line(bool(repo) or bool(vault_opt), "vault %s%s" % (root, (" covers this checkout as `%s`" % repo) if repo else ""),
             "you are inside the vault, not a covered checkout: run this from the project")
        idx = vaultlib.load_index()
        owned = len(idx.get("paths") or {})
        line(owned > 0, "%d note(s), %d owned path(s)" % (len(idx["notes"]), owned),
             "no note owns code yet, so the file pointer can't fire: run /lightkeeper:seed")
        ran = last_hook_run()
        if ran:
            mins = int(ran[0] // 60)
            print("ok   hooks last ran %s ago (%s)" % (
                "%d min" % mins if mins < 120 else "%d h" % (mins // 60),
                ", ".join("%s %d" % kv for kv in sorted(ran[1].items())) or "no counts"))
        else:
            # not a failure: a fresh install has simply not had a session yet
            print("--   no hook has run for this vault in the last 24 h. Start a session in the "
                  "checkout; if the primer doesn't appear, check the plugin is enabled (/plugin) "
                  "and run once with VAULT_HOOK_DEBUG=1 to see hook errors.")

    if shutil.which("vault"):
        print("ok   `vault` is on PATH")
    else:
        # the slash commands don't need it, so this is advice, not a failure
        local = Path.home() / ".local" / "bin"
        if (local / "vault").is_file():
            print("--   `vault` is installed in %s, but that folder is not on your PATH. The slash "
                  "commands work without it; for the shell: export PATH=\"$HOME/.local/bin:$PATH\"" % local)
        else:
            print("--   `vault` is not on PATH. The slash commands work without it; for the shell: "
                  "python3 %s init --install-cli" % (PLUGIN / "bin" / "vault"))
    if root:
        print("to stop using this vault here: vault init --forget")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
