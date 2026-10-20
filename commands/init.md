---
name: init
description: Create a new knowledge vault for this project, or clone or adopt an existing one; wire the CLI and the git hook; tell the user how to open it in Obsidian.
argument-hint: <vault path> --name NAME --repo <checkout> [--repo <checkout>] [--install-cli] [--git-hook] [--backup-remote <url>] | --clone <url> | --adopt <existing vault>
---

Create or connect a vault.

If `$ARGUMENTS` contains none of `--repo`, `--clone` or `--adopt`, stop and ask the user first: the path of the code checkout the vault should cover (several `--repo` flags are allowed), the name of the vault, and where the vault folder should go. Build the argument list from their answers.

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/init.py" $ARGUMENTS
```

Show the user the output unchanged. It names the vault folder, the repos it watches, whether the `vault` CLI and the post-merge git hook were installed, and the result of the first `vault check --write`.

Then tell the user, in two lines:

1. Open the vault folder in Obsidian with **Open folder as vault**. `Home.md` is the entry page. `World.canvas` is the map; the tool regenerates it, so don't edit it by hand.
2. Restart Claude Code inside the repo so the hooks pick the vault up. Then run `/lightkeeper:seed` to propose the first domains and module stubs.

If `init.py` reports an error, show it and stop. Don't create the folders by hand.
