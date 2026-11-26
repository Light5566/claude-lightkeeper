# Lightkeeper on Hermes Agent and Codex

[Back to the README](../README.md)

## Hermes Agent

The repo root is also a [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin (`plugin.yaml`, `__init__.py`). Install it, enable it, then create a vault the same way:

```
hermes plugins install Light5566/claude-lightkeeper
hermes plugins enable lightkeeper
cd ~/code/myapp && python3 ~/.hermes/plugins/lightkeeper/bin/vault init
```

The registry file keeps its historical name, `~/.claude/vaults`; Claude Code is not needed. What you get, in three tiers:

- **CLI compatible.** `vault` works from any shell. `--install-cli` puts it on your PATH, and the launcher finds the Hermes install.
- **Workflow integration.** The three skills and the five procedures are Hermes skills: `lightkeeper:knowledge-vault`, `lightkeeper:vault-sync`, `lightkeeper:vault-tidy`, `lightkeeper:init`, `lightkeeper:seed`, `lightkeeper:tidy`, `lightkeeper:trace` and `lightkeeper:release`. The first-turn primer names them, and the agent loads one with `skill_view`.
- **Automatic lifecycle.** The adapter runs the same hook scripts Claude Code runs, through Hermes's plugin hooks. Exactly what is wired, and where it differs:

| Behaviour | In Hermes |
|---|---|
| Session primer | appended to your first message in a new session (`pre_llm_call`); not on a continued session, and not again after a context compaction |
| Prompt hints | appended to the message that triggered them |
| Edit pointer | after the edit, not before: it arrives as a `lightkeeper` field inside the JSON result of `write_file` or `patch` (`transform_tool_result`). The agent learns which note owns the file it just changed and reads its Gotchas before going further. What names notes before any edit is the prompt hint and the primer |
| Stop reminder | Hermes's verify gate (`pre_verify`): on a turn in which Hermes saw file edits, the reminder comes back as a synthetic user turn, once per answer, and the agent keeps working; a turn without file edits does not trigger it |
| Notice to you | the reminder is shown once more when the session ends (`/new`, quit), never to the model |

It needs a session whose working directory is a covered checkout, and the local terminal backend. Nothing blocks, as in Claude Code. Lightkeeper is not a memory provider, so it sits beside Hermes's own memory and any memory plugin. Hermes 0.22 or newer: tested with a real model on stable 0.22.2 in `hermes chat -q` mode, covering `patch` and `write_file`, the edit pointer, the verify-gate reminder, the note update and the session-end notice; not yet verified are the messaging gateways, interactive multi-turn sessions, turns after a context compaction, concurrent sessions on one gateway, and host-unified main builds. For development, `bash check.sh` drives the adapter with a fake plugin context; on a machine with Hermes, run `hermes plugins validate .` and `hermes plugins doctor . --ci`.

## Codex

Codex installs plugins from the same marketplace, and runs Lightkeeper's hooks through a small adapter in `codex/`:

```
codex plugin marketplace add Light5566/claude-lightkeeper
codex plugin add lightkeeper@claude-lightkeeper
```

Create a vault from a shell inside your project, or skip this if you already have one from Claude Code. With no arguments it covers the repo you are in and installs the `vault` command, so every later command is just `vault …`. `<version>` is the folder Codex made for the version it installed:

```
python3 ~/.codex/plugins/cache/claude-lightkeeper/lightkeeper/<version>/bin/vault init
```

| Behaviour | In Codex |
|---|---|
| Session primer | as in Claude Code, including the short reminder after a compaction |
| Prompt hints | as in Claude Code |
| File pointer | for every file an `apply_patch` adds, updates, deletes or moves. The agent reads it with the patch's result, so it learns the owning note just after the edit, as in Hermes. Codex reads files through the shell, so there is no read pointer: what names notes before any edit is the prompt hint and the primer |
| Stop reminder | shown to you, and once per session sent back to the agent as its next prompt: Codex's Stop hook has no context channel, so the adapter uses `decision: block` with the reminder as the reason |
| Skills | `knowledge-vault`, `vault-sync` and `vault-tidy`. The five slash commands are Claude Code's; in Codex, use the `vault` CLI |

The first time the Codex TUI starts after the install, it asks you to review the plugin's hooks: trust all four. A hook switched off there stays off until you switch it back on in `/hooks`. Tested with a real model on Codex CLI 0.166.0-alpha.6 in `codex exec` mode, covering the session primer, prompt hints with a glossary term, the file pointer on `apply_patch`, and both Stop paths: quiet once the note is updated; otherwise the reminder goes back to the agent, which updates the note or says why not, and the next Stop stays quiet. Not yet verified: interactive TUI sessions and turns after a context compaction. For development, `bash check.sh` drives the adapter with fake payloads.
