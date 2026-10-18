---
name: release
description: Record a release in the vault — draft 7 Releases/vX.Y.Z.md from what moved per owning note, list the commands and flags, and sweep for notes the release should have touched.
argument-hint: vX.Y.Z [--since <ref>]
---

Record a release. `$ARGUMENTS` is the version and, optionally, `--since <ref>` for the start of the window. Without it the window starts at the previous release.

1. Run:

```bash
vault release $ARGUMENTS --json
```

It prints the window (`<start>..<production_ref>`), the commits, the changed files grouped by owning note, the files matching no note, and the version-log lines added in the window. If it reports that the version is not on the production branch, stop and say so. A release note describes production.

2. **Draft `7 Releases/vX.Y.Z.md`** from `_templates/Release.md`:
   - the one-sentence summary in plain words;
   - *Modules touched*: one reasoned link per owning note, saying **what** changed there. Read the diffs for the group, not the commit subjects;
   - *Flows affected* and *Decisions made* where the diffs show them;
   - *Commands to run*: migrations, seeders and one-off patches the window added, with when to run them;
   - *Flags flipped*: every flag whose default or value changed, from → to.
3. **The sweep.** List every owning note in the report whose `updated` predates the start of the window. Those notes were missed when their code changed. Fix each one now from the diffs (*How it works*, *Gotchas*, `updated`), and promote stubs whose module clearly moved. Then add `- [[vX.Y.Z]] — <what changed>` to each touched note's *History*.
4. **Files matching no note** go through the trigger table: a stub for a new module, or a *Where it lives* row on an existing note.
5. **Flip `in-progress` claims** the release made true, after verifying each with `git merge-base --is-ancestor` plus a content grep.
6. Run `vault check --write` until it exits 0, then commit the vault with a message naming the version and the notes touched.
