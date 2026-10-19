# Changelog

All notable changes to claude-vault. The plugin version lives in `.claude-plugin/plugin.json`.

## 2.1.5 - 2026-10-19

### Fixed
- A vault commit that only touches `.obsidian/` no longer silences the Stop reminder for the next six hours. Uncommitted Obsidian settings were already ignored; committed ones now are too.

## 2.1.4 - 2026-10-19

### Fixed
- New vaults now get the Obsidian settings the README promised: the graph colour groups, the core plugins (Properties, Bases, canvas, templates) and the templates folder. They were missing from the scaffold, so the graph opened grey. The demo vault has them too.

## 2.1.3 - 2026-10-19

### Fixed
- On narrow screens the HTML map refits the graph when opening a note shrinks it, until the viewer zooms or pans themselves.

## 2.1.2 - 2026-10-19

### Fixed
- The HTML map's reader panel is wider and its tables scroll sideways instead of squeezing, so a flow's steps table shows every column.

### Added
- A gallery on the Pages site: interactive maps of Excalidraw, Mastodon, Gitea, Paperless-ngx and BookStack, each pinned to a commit and checked against its code.

## 2.1.1 - 2026-10-19

### Fixed
- The HTML map export fits the graph on first paint instead of animating into place, so a screenshot or a slow page never catches it half-laid-out.

### Added
- README images (the hooks firing, the demo map), a Chinese README, this changelog, and the social preview card in `docs/assets/`.

## 2.1.0 - 2026-10-19

### Added
- **PR comment bot**: `action/`, a composite GitHub Action (`uses: Light5566/claude-vault/action@main`) that comments on a pull request with the vault notes that own its changed files and the files that match no note. Advisory only; never fails a check, never writes.
- The repo runs the action on its own pull requests against the demo vault.

## 2.0.0 - 2026-10-19

First public release.

### Added
- The engine (`lib/`): vault resolver (explicit path, `VAULT_ROOT`, the folder you are in, or the `~/.claude/vaults` registry matched by git remote or path, longest match wins), index builder, `find`, `check`, `sync`, `status`, `log`, `release`, `export`, `init`.
- Four Claude Code hook events with five behaviours: session primer (and a post-compaction reminder), prompt hints with a once-per-session decision nudge, pre-edit pointer with stub-aware wording, Stop reminder naming the owning notes.
- Skills `knowledge-vault`, `vault-sync`, `vault-tidy`; commands `/vault:init`, `/vault:seed`, `/vault:tidy`, `/vault:trace`, `/vault:release`.
- Scaffold for a new vault: Home, Conventions, How to update, five templates, Obsidian config with graph colour groups, four Bases views.
- Generated files on `vault check --write`: Coverage, Vault Changelog (from the vault's git history), Attention (consolidate, re-verify, promote, path rot, link rot), World.canvas.
- Single-file interactive HTML map (`vault export --html`).
- `vault init` presets for common layouts, `--clone` for a team vault, `--adopt` for an existing Obsidian vault, `--git-hook` (post-merge and pre-push report hooks), `--backup-remote`.
- Secrets rule in `check` (warnings by default, `--strict` to fail, `secrets_allow` in vault.json).
- Demo vault over BookStack in `demo/` and its map in `docs/`.
