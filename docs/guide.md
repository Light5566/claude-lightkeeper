# Lightkeeper: configuration, teams, keeping the map honest

[Back to the README](../README.md)

## Configuration

`_meta/vault.json` in the vault:

```json
{
  "name": "My App",
  "repos": {
    "myapp":     {"remote": "github.com/acme/myapp", "watched": ["app", "routes", "database/migrations"],
                  "production_ref": "origin/main", "version_log": "CHANGELOG.md"},
    "myapp-web": {"remote": "github.com/acme/myapp-web", "watched": ["app", "components", "src"],
                  "production_ref": "origin/main"},
    "local-only": {"path": "~/code/experiment", "watched": ["src"]},
    "ops":        {"remote": "github.com/acme/monorepo", "root": "apps/ops", "watched": ["src"]}
  },
  "generic_dirs": ["app/Services"],
  "noise_files": ["TODO.md"],
  "stop_window_hours": 6,
  "tidy": {"max_words": 4000, "max_gotchas": 20, "stale_days": 60, "churn_commits": 5}
}
```

- `repos` is what the hooks route on: a checkout matches by `remote` substring (any URL form) or by `path`; `root` scopes a monorepo sub-app. Longest match wins. The key is the value of the `repo:` frontmatter field.
- `watched` are the directories the Stop reminder watches. `vault init` detects them from the layout.
- `generic_dirs` extends the built-in list of container directories a note may never own wholesale.
- `tidy` sets the attention thresholds.
- `_meta/local.md`, if present, holds this vault's own rules (branch names, changelog format, data-privacy wording). Every skill reads it.

Environment overrides: `VAULT_ROOT` (use this vault), `VAULT_WATCHED`, `VAULT_WINDOW_HOURS`, `VAULT_STOP_NUDGE=quiet` (keep the Stop reminder out of the agent's context, show it only to you).

## Teams

The vault is its own git repo. Share it the way you share code:

- Each person installs the plugin and runs `/lightkeeper:init --clone <url> --repo <checkout>`. Their hooks now point at the same map.
- Colleagues' pushes arrive with no hook attached, so the map drifts. `vault sync` reports everything that landed on each repo since the vault last caught up, grouped by the notes that own the changed files, and the `vault-sync` skill walks the catch-up. Advance the cursor only after the notes are updated.
- The `post-merge` and `pre-push` git hooks that `vault init --git-hook` installs print how far the vault is behind the branch. They never block, and they work for teammates who do not use Claude.
- `vault init --backup-remote <url>` makes every vault commit push itself, so a one-machine vault is never more than a commit behind its backup.
- **The PR comment bot.** `uses: Light5566/claude-lightkeeper/action@main` in a code repo's workflow comments on every pull request with the notes that own its changed files, what else each of those notes connects to and why, its first Gotcha, and the files that match no note. Advisory, never blocks. Setup in [action/README.md](../action/README.md).

## Keeping the map honest

`vault check --write` computes maintenance signals into `_meta/Attention.md`:

| Signal | Rule |
|---|---|
| consolidate | more than `max_words` words or `max_gotchas` Gotcha bullets |
| re-verify | `updated` older than `stale_days` **and** at least `churn_commits` commits touched the note's files since |
| promote | a stub whose files keep changing |
| path rot | a *Where it lives* path that exists in no worktree or committed tree |
| link rot | a link reason names a `Class::method` that no file defines |

The session primer mentions the count once a day. `/lightkeeper:tidy` works the list: it regroups and dedupes Gotchas without dropping a single trap, re-reads the diff behind a stale note before confirming or fixing it, and promotes stubs from the code.

`_meta/Vault Changelog.md` is derived from the vault's git history on every `--write`, so the history of what the map learned, and when, is never hand-kept. `World.canvas` is regenerated the same way: one group per domain, modules inside, cross-domain links with their reasons.

## Notes and branches

One map for every branch has a catch: a note written on a feature branch is also what an agent on `main` reads. So the hooks remember which branch a note was last edited on. When the agent opens a file whose note was last written on a branch the current checkout doesn't contain, the file pointer says so and tells it to check the note against the code in front of it. Once the branch is merged, the warning stops by itself. `vault status` lists these notes. The record is kept per machine, beside the vault registry, and nothing is written into the vault or the repo.
