---
name: trace
description: Follow a route, console command or job through the code and draft a 3 Flows note for the journey, with one reasoned link per module crossed and the reverse link on each module note.
argument-hint: <route name | console command | job class>
---

Trace `$ARGUMENTS` and write it up as a flow.

1. **Resolve the vault** with `vault status`, then `vault find $ARGUMENTS` to see whether a flow note already covers it. If one does, update that note instead of writing a second one.
2. **Find the entry point**: the route definition, the console command class, or the job's handle method. Confirm the file exists.
3. **Follow the call chain** in the order the code runs: controller → request validation → service → repository or model → events and listeners → queued jobs → notifications → outside calls. Read the code, not the names. Stop at the boundary where the journey ends for the user: a response, a persisted state, a message sent.
4. **List every module crossed, in order.** For each step, `vault find --paths <file>` gives the owning note. A step whose file maps to no note is a gap: tell the user, and either add a *Where it lives* row to the right module note or propose a stub.
5. **Draft the flow** from `_templates/Flow.md` into `3 Flows/<Journey>.md`: *What happens* in business language; the *Steps* table with one row per step, *Where* as `Class::method` (never a full path; the module note owns the path), *Module* as the owning note; *Modules crossed* with **one reasoned link per crossing**; *Where it breaks* from what the code and tests show (partial states, retries, idempotency gaps).
6. **Add the reverse link** on each crossed module note's *Connects to*: `- [[<Journey>]] — <what this module does for the flow>`. Bump each note's `updated`.
7. Run `vault check --write` until it exits 0.
8. **Show the diff** (`git -C <vault> diff`) and ask before committing. Commit with a message naming the flow and the module notes touched.
