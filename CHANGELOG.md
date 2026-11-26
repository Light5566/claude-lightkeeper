# Changelog

All notable changes to Lightkeeper, formerly claude-vault. The plugin version lives in `.claude-plugin/plugin.json`.

## 2.11.0 - 2026-11-26

The first five minutes. A survey of eight similar tools and a walk through our own first run found too many decisions before the first note, silence when nothing was set up, and no way to check or undo the setup.

### Added
- **`/lightkeeper:init` with no arguments.** From a session inside your project it covers the repo you are in, names the vault after its folder, puts it in `~/vaults/<name>` and installs the `vault` command. It shows those choices and asks once. `vault init --plan` prints them and changes nothing; `--no-cli` skips the launcher. Every explicit form (`<path> --name --repo`, `--clone`, `--adopt`, `--install-cli` alone) works as before.
- **`vault doctor`.** One screen: Python and git, the plugin and its version, the registry, whether this folder is covered and by which vault, whether any note owns code, whether `vault` is on PATH, and when the hooks last ran. A fix is printed beside each problem, and it exits 1 when something needs fixing.
- **`vault init --forget [<vault>]`.** Stops using a vault here: removes its registry line and the report-only git hooks Lightkeeper installed. The vault folder is never deleted; `--adopt` brings it back.
- **A message when nothing is set up.** The first session in a git checkout that no vault covers shows the user one line saying to run `/lightkeeper:init`, once per checkout ever. `LIGHTKEEPER_QUIET=1` hides it.
- **A line when the vault is empty.** Until a module or integration note exists, the session primer says the file pointer has nothing to point at and to run `/lightkeeper:seed`.

### Changed
- **The slash commands no longer need `vault` on your PATH.** seed, tidy, trace and release call the plugin's own launcher, so they work straight after install.
- **One order everywhere: init, seed, done.** The file pointer works in the same session once notes own files, so no restart is needed; the session primer shows from the next session. The README, the init command and init's last line now agree, and init offers to seed straight away.
- **README.** The first screen is three lines to a working map and says nothing is written into your repo. Configuration, teams, keeping the map honest and branch notes moved to `docs/guide.md`; Hermes Agent and Codex to `docs/agents.md`. 3,483 words became 2,184. Same in 中文.
- The Hermes and Codex install lines use the zero-argument `vault init`.

### Fixed (26 Nov, after a walk through the first run)
- `vault doctor` tells apart a launcher that isn't installed from one that is installed in `~/.local/bin` but not on your PATH, and gives the right line for each.

## 2.10.0 - 2026-11-25

### Added
- **A glossary word can mean different things in different modules.** When a term appears in a prompt, the hint now gives its meaning, then one line per note it shows up in, taken from the reasons on its *Where it shows up* links (`in Payment: …`, `in Order: …`), up to three. Notes already in play this session, or named in the same prompt, come first. It ends with the first line of *Not to be confused with* (`not: …`), so a correct meaning isn't applied in the wrong place. A term whose links carry no reasons keeps the old `(shows up in …)` form.
- The term template says to write a module's own meaning on that module's line, and what an outsider would wrongly assume under *Not to be confused with*. Existing term notes need no change; add reasons and that section to get the new lines.

## 2.9.0 - 2026-11-25

### Added
- **Branch-tied notes.** The vault is one map for every branch and worktree, so a note written on a feature branch is also what an agent on `main` reads. The hooks now remember, per note, the branch and commit of the checkout the agent was in when it edited the note. When the file pointer names a note that was last written on a branch the current checkout doesn't contain, it adds one line saying so and telling the agent to check the note against the code in front of it. On the branch itself, and once the branch is merged, it says nothing. `vault status` lists these notes on a `branch notes:` line (`branch_notes` in `--json`). Works the same in Claude Code, Hermes Agent and Codex.
- The record is kept per machine in `~/.claude/vaults-branches.json`, beside the registry; nothing is written into the vault or the repo. It is trusted only while the note's modification time still matches the recorded edit, so a note changed since by hand, by a pull or on another machine is not judged.

### Fixed
- The file pointer now recognises the vault's own files through a symlinked path (for example `/var` and `/private/var` on macOS), so editing a note never triggers a pointer.

## 2.8.0 - 2026-11-05

### Added
- **`vault export --agents-md`.** Prints a short block for `AGENTS.md`, `CLAUDE.md` or `GEMINI.md`, so agents that don't run Lightkeeper's hooks still find the map. The block says where the vault is: its path and, when it has one, its git remote with any credentials removed, plus the command to clone it. It says how to search the vault, and that updating the owning note is part of the definition of done. Then it lists, at most 15 rows, the module and integration notes that own code in this repo, with their files, full notes first. The command only prints: nothing is written for you, and no hook runs it. To refresh, run it again and replace the text between the markers. `--repo KEY` picks the repo when one vault covers several.

### Changed
- README: the Codex section says what the live runs covered, and that a Codex agent reads the file pointer together with the patch's result.

## 2.7.0 - 2026-11-05

### Added
- **Codex support.** Codex installs plugins from the same marketplace: `codex plugin marketplace add Light5566/claude-lightkeeper`, then `codex plugin add lightkeeper@claude-lightkeeper`. `.codex-plugin/plugin.json` points Codex at the three skills and at `codex/hooks.json`, whose hooks run `codex/adapter.py`. The adapter drives the same hook scripts through their stdin/stdout contract and translates the two places where Codex differs. The file pointer reads the files an `apply_patch` adds, updates, deletes or moves, and fires before the patch lands. The Stop reminder, which Codex's Stop hook can't carry as context, goes back to the agent once per session as `decision: block` with the reminder as its reason. The README's Codex section lists exactly what is wired.
- The `vault` launcher finds a Codex install in `~/.codex/plugins/cache`.

### Unchanged
- Claude Code and Hermes Agent: nothing they see changed.

## 2.6.0 - 2026-11-05

### Added
- **Glossary notes.** A word the codebase uses in its own way gets a short note in `9 Glossary` with `type: term`: what it means here and where it shows up (new template `_templates/Term.md`). When the word, or one of its aliases, appears in a prompt, the prompt hint lists it apart from the module notes, with its meaning, up to three terms. `vault check` accepts the type and doesn't call a term an orphan, because terms are reached by name, not by link. New vaults get the folder, a brown graph colour and a legend row; in an existing vault, create `9 Glossary/` and copy the template.
- **The PR comment says what else a change touches.** Under the table, each owning note now shows its top reasoned links, which are the blast radius, and its first Gotcha. Wikilinks render as plain names, and an `@` in a note can't mention a GitHub user.

## 2.5.0 - 2026-11-05

### Added
- **The file pointer also fires on reads.** PreToolUse now matches `Read` as well as the edit tools, so the note that owns a file arrives the first time the agent opens it, while it is still planning, not only when it is about to write. Same once-per-note rule. Claude Code makes the agent read a file before editing it, so the read pointer is usually the one that fires, and it carries the definition-of-done line.
- **`vault status --session`** shows what the hooks did in the latest session, or in one picked with `--session=ID`: how often each hook ran and how often it told the agent something, the notes they surfaced, and which of those the vault has updated since the session started. `--json` for scripts. To make this possible, the hook runner now counts every run in the per-session state.

### Fixed
- **After a compaction, the hints and the pointer name a note again.** The once-per-session state survived compaction, so every note surfaced before it stayed silent afterwards, although its text had left the context with the summary. The post-compaction reminder now lists the notes that were in play and re-arms them.

### Unchanged
- Hermes Agent: the pointer still arrives with the result of `write_file` and `patch`; reads are not wired there yet. Its hook runs count in the same session report.

## 2.4.4 - 2026-10-21

### Changed
- README, Hermes section: states what was verified with a real model (Hermes stable 0.22.2, `hermes chat -q`) and what was not (messaging gateways, interactive multi-turn sessions, turns after a compaction, host-unified main builds).
- `check.sh`: `write_file` and `patch` results come out of the adapter with every field Hermes reads intact (`bytes_written`, `success`, `files_modified`, `resolved_path`) and only the `lightkeeper` field added; an exception inside the adapter checks now fails the run.
- Adapter docstring says edit pointer, as the README does.

## 2.4.3 - 2026-10-21

### Fixed
- Hermes adapter: the edit pointer now goes inside the tool's JSON result, as a `lightkeeper` field, instead of being appended as text. Appended text made the result unparsable for Hermes, which then did not record the file as edited, so its verify gate never ran and the Stop reminder only reached the user as the session-end notice. Found in a live run against Hermes 0.22.2.

## 2.4.2 - 2026-10-21

### Changed
- Hermes adapter: per-session state is keyed only by the `session_id` Hermes passes to each hook. The "last session seen" fallback is gone, so a gateway serving several chats can no longer mix one chat's dedup state into another's.
- The README's Hermes section calls the file pointer what it is there: an edit pointer that arrives after the edit, with the prompt hint and the primer as the signals that name notes before an edit.

## 2.4.1 - 2026-10-21

### Changed
- The Pages site (the gallery, the README images and GIF) moved from `docs/` on `main` to the `gh-pages` branch. A plugin install no longer carries the 8 MB site, and install scanners no longer read it. The README links its images from the published site.

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
