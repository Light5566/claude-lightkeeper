---
type: meta
updated: 2026-10-18
tags: [meta]
---

# How to update this vault

The human-readable copy of the ritual. The machine-readable copy is the `knowledge-vault` skill the Claude Code plugin loads, and `vault-sync` is the catch-up for work that landed without a vault update. Keep this note and the skill in step. Rules specific to this vault go in `_meta/local.md`.

## Read before you write

The vault is the retrieval layer. Query it before a change, not only after:

```bash
vault find order refund                               # topic → notes + blast radius
vault find --paths app/Services/RefundService.php     # the files you'll touch → owning notes
```

Read the matched note's *How it works* and *Gotchas* before changing that area. The neighbours `vault find` prints, each with the reason the link exists, are the blast radius: the other notes to check when your change ripples. Inside a covered repo the hooks do the lookup for you: a hint on your prompt, a pointer before your first edit of a documented file. When a hook surfaces a note, actually read it.

## The rule

> Updating this vault is part of the definition of done, exactly like the changelog entry. A change that ships without its note is incomplete.

Do it in the same working session as the code, while the reasoning is still in your head. A week later you remember what you changed but not why, and the why is the only part the diff can't give back.

## Trigger table

| What changed | What to touch |
|---|---|
| **New module** | New note in `2 Modules` + a reasoned link from its `1 Domains` note |
| **Enhanced module** | That note's *How it works* / *Gotchas*; bump `updated`; promote `depth: stub → full` |
| **Behaviour spanning modules** | A `3 Flows` note, plus the reasoned link on **both** module notes |
| **New or changed third party** | `4 Integrations` |
| **New convention, or a trap that will bite again** | `5 Platform` |
| **A non-obvious why**: a client ruling, a reversal, a deferred refactor | `6 Decisions` |
| **Renamed or removed module** | Rename the note (Obsidian fixes inbound links) or set `status: deprecated`. Never delete silently |
| **Release reached the production branch** | `7 Releases/vX.Y.Z.md` + the reconcile sweep below |

The canvas is not on the list. `vault check --write` regenerates `World.canvas` from the notes.

## The 60-second version

Most changes are an enhancement to one existing module. That is three edits:

1. Open `2 Modules/<Thing>.md`.
2. Amend *How it works*, and *Gotchas* if you just lost an hour to something.
3. Bump `updated` to today.

If the change made two modules touch in a new way, add the reasoned link on **both** notes. One-directional links are how the map starts drifting from reality.

If the work is still on a branch, say so: `status: in-progress` on a new note, or a "(on `develop`, not yet on `main`)" marker on the paragraph you added to a shipped note. Flip it when you verify the merge.

Then:

```bash
vault check --write      # must exit 0
git -C <vault> add -A && git commit -m "Payment: capture retries; Gotcha on webhook ordering"
```

The vault is its own repo. The vault commit is part of the ritual and is separate from the code commit.

## Release-cut reconcile

When a version reaches the production branch:

1. Create `7 Releases/vX.Y.Z.md` from the Release template. `vault release vX.Y.Z` prints the window and the notes whose files moved.
2. List every module note the release touched, each with what changed.
3. Sweep for misses: a note whose `updated` predates the previous release but whose files moved in this one was skipped. Fix it now.
4. Record the commands the release needs (migrations, seeders, one-off patches) under *Commands to run*, and the flags it flips under *Flags flipped*.
5. Flip `in-progress` claims the release made true, after verifying each one.

`/lightkeeper:release vX.Y.Z` walks these steps.

## Catching up

If a session shipped code without updating the vault, don't reconstruct from memory. Read the changelog entry and the actual diff, then write what the code says. A note written from a hazy recollection is worse than a stub: a stub is honestly thin, a bad note is confidently wrong.

Other people's pushes have no hooks pointed at this vault. `vault sync` reports everything that landed on each watched repo's production branch since the vault last reconciled, grouped by owning note. The `vault-sync` skill walks the catch-up.

## Keeping yourself honest

- **Five advisory hooks** run in every repo this vault covers: a session primer; prompt-matched note hints, with a once-per-session nudge when a prompt sounds like a decision; a pointer at the owning note before an edit; a Stop reminder that names the notes the session's changed files belong to when the vault didn't move; and a reminder to re-query the vault before context is compacted. None of them block anything, and none can tell a typo fix from a new module. Use judgement. `VAULT_STOP_NUDGE=quiet` silences the Stop reminder for one shell when you need it to.
- **`vault sync`** closes the gap the hooks can't see: colleagues' pushes, merges done on the hosting site, sessions on another machine. `--advance` moves the cursor only once the notes are updated.
- **`_meta/Attention.md`** is regenerated on every check and lists what needs a human: notes to consolidate, notes to re-verify because their code moved, stubs to promote because their files keep changing, and paths or link reasons that no longer match the code. The `vault-tidy` skill works the list.
- **`vault status`** shows all of this in one screen. Run it when you come back to a project after a while.
- Sort by *Modified* in Obsidian. A module you know is active with a three-month-old note is a lie waiting to be found.
