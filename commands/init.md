---
name: init
description: Create a new knowledge vault for this project, or clone or adopt an existing one; wire the CLI and the git hook; tell the user how to open it in Obsidian.
argument-hint: "[nothing: a vault for this repo] | <vault path> --name NAME --repo <checkout> [--git-hook] [--backup-remote <url>] | --clone <url> | --adopt <existing vault> | --forget"
---

Create or connect a vault.

If `$ARGUMENTS` names no vault path and contains none of `--clone`, `--adopt` or `--forget`, the defaults apply: a vault for the checkout this session is in, named after its folder, in `~/vaults/<name>`, with the `vault` command installed. First run the line below with `--plan` added, which changes nothing and prints those defaults. Show the user that one line and ask once: go ahead, or change something (the name, the folder, more checkouts with `--repo`, `--no-cli`, `--git-hook`). If it prints that the checkout is already covered or is not a git checkout, show that and stop.

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/init.py" $ARGUMENTS
```

Show the user the output unchanged. It names the vault folder, the repos it watches, whether the `vault` CLI and the post-merge git hook were installed, and the result of the first `vault check --write`.

Then tell the user, in two lines:

1. The vault has no notes about the code yet. Offer to run `/lightkeeper:seed` now, in this session: it proposes the first domains and module stubs and writes nothing until they approve. The file pointer works as soon as notes own files; the session primer shows from the next session.
2. To look at the map, open the vault folder in Obsidian with **Open folder as vault** (`Home.md` is the entry page; `World.canvas` is regenerated, so don't edit it by hand). `vault doctor` checks the setup at any time.

If `init.py` reports an error, show it and stop. Don't create the folders by hand.
