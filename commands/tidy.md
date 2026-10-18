---
name: tidy
description: Work the vault's attention list (consolidate, re-verify, promote, path rot, link rot) or tidy one named note, with a before/after summary.
argument-hint: [note name]
---

Load the `vault-tidy` skill and follow it.

1. Run `vault status`. If `$ARGUMENTS` names a note, work only that note. Otherwise take the top items of the attention list, at most five in one pass.
2. For each note, record the word count and the number of *Gotchas* bullets before you start.
3. Apply the skill per signal. A tidy never changes meaning. Keep every specific fact.
4. Run `vault check --write` until it exits 0.
5. Show the user one line per note: `<note>: <words before>→<after> words, <gotchas before>→<after> Gotchas, <signal cleared>`.
6. Commit the vault with a message naming each note and what was done to it.
