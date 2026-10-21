# Changelog

All notable changes to Lightkeeper, formerly claude-vault. The plugin version lives in `.claude-plugin/plugin.json`.

## 2.4.0 - 2026-10-21

### Added
- **Hermes Agent support.** The repo root is now also a Hermes plugin: `plugin.yaml` and `__init__.py` map Hermes's plugin hooks onto the same hook scripts Claude Code runs. `hermes plugins install Light5566/claude-lightkeeper`, then `hermes plugins enable lightkeeper`. The session primer, prompt hints, the pre-edit pointer (delivered with the result of `write_file` or `patch`), the Stop reminder (through Hermes's verify gate, on turns where Hermes saw file edits) and a notice at session end are wired; the three skills and the five commands become `lightkeeper:*` skills. The README's Hermes section lists exactly what is wired and how it differs.
- The `vault` launcher finds a Hermes install (`~/.hermes/plugins`), so `--install-cli` works without Claude Code.
- `check.sh` exercises the adapter with a fake plugin context, no Hermes needed.

### Changed
- Agent-neutral wording in the skills, `init`, the scaffold and `vault init`'s closing line.
- `lib/hooks/run.py` loads hooks with `importlib`; the linter's private-key pattern and the action README's example no longer trip install scanners.

### Unchanged
- Everything Claude Code sees: `hooks.json`, the hook scripts' contract, commands, skills, vaults and `vault.json`.

## 2.3.2 - 2026-10-20

### Fixed
- `vault init --git-hook` no longer overwrites a `post-merge` or `pre-push` hook it didn't write. It used to treat any hook containing the text `claude-vault` as its own, so a hook that merely mentioned that word, such as a path to another tool, was replaced. It now looks for its own header line, and the install message names only the hooks it actually wrote.

## 2.3.1 - 2026-10-20

### Fixed
- The `/lightkeeper:seed` and `/lightkeeper:tidy` headers quote their argument hints. A hint that starts with a bracket is read by YAML as a list, which broke the seed command's header in the plugin directory's validator.

## 2.3.0 - 2026-10-20

### Changed
- **The plugin is now called `lightkeeper`**, shown as Lightkeeper. The plugin directory asks for a distinctive name, and `vault` was a generic word that matches a well-known product. Commands are now `/lightkeeper:init`, `/lightkeeper:seed`, `/lightkeeper:tidy`, `/lightkeeper:trace` and `/lightkeeper:release`. Install with `/plugin install lightkeeper@claude-lightkeeper`.
- **Unchanged:** the `vault` command-line tool, your vault folders and their `vault.json`, the hooks and the git hooks. The `vault` launcher now finds the plugin under either name.
- To move an existing install: `claude plugin uninstall vault@claude-lightkeeper`, then `claude plugin marketplace update claude-lightkeeper` and `claude plugin install lightkeeper@claude-lightkeeper`. If you installed the `vault` command with `--install-cli`, run `/lightkeeper:init --install-cli` once so the launcher knows the new name.
- The README GIF is re-encoded at 1040 px (4.6 MB), under the directory's 5 MiB file limit.

## 2.2.1 - 2026-10-19

### Fixed
- `vault export --html <file>` works as the README says: `--html` is accepted (`--out` still is), and the vault covering the current folder is used when `--vault` is not given.

## 2.2.0 - 2026-10-19

### Changed
- **Renamed to Lightkeeper.** The repo is now `Light5566/claude-lightkeeper`, the marketplace is `claude-lightkeeper` and the gallery lives at `light5566.github.io/claude-lightkeeper`. The plugin itself is still called `vault`, so `/vault:…` commands, the `vault` CLI, your vaults and their git hooks are unchanged.
- To move an existing install: `claude plugin marketplace remove claude-vault`, then `claude plugin marketplace add Light5566/claude-lightkeeper` and `claude plugin install vault@claude-lightkeeper`.

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
