---
type: meta
updated: 2026-10-18
tags: [meta]
---

# BookStack — the world

A living map of how BookStack is built and how the pieces connect. Business areas live in `1 Domains`, the things you can point at in `2 Modules`, the journeys that cross them in `3 Flows`, the outside systems they call in `4 Integrations`, the conventions and traps every module inherits in `5 Platform`, the reasons things are the way they are in `6 Decisions`, what moved in each version in `7 Releases`, and one orientation note per codebase in `8 Repos`: [[BookStack]].

> **[[World.canvas|World]]** — the visual map: domains as groups, modules inside them, the strongest links between them. The tool regenerates it on every `vault check --write`. Never edit it by hand.
>
> **Before writing anything here**, read [[Conventions]]. **After shipping anything**, read [[How to update]].

## Finding things

The vault is queryable. People and agents use the same tool:

```bash
vault find payment capture                            # topic → notes + blast radius
vault find --paths app/Services/PaymentService.php    # file → the notes that own it
vault status                                          # coverage, stale notes, what needs attention
vault sync                                            # what landed on the production branch since the vault last caught up
vault check --write                                   # lint, rebuild the index, regenerate the generated files
```

Every hit prints the note's one-liner, its `status` and `updated`, and its linked neighbours **with the reason each link exists**. That neighbour list is the blast radius of a change: the other notes to check before you touch this one. Inside a repo this vault covers, the Claude Code hooks surface the same notes without being asked.

## The domains

One note per business area in `1 Domains`. Fill this table as the domains take shape, one line each.

| Domain | What lives there |
|---|---|
| [[Content]] | Shelves, books, chapters and pages |
| [[Access & Permissions]] | Who can log in and what they may see |
| [[Users & Settings]] | User accounts, preferences, instance settings, maintenance and the audit log. |
| [[Search & References]] | Finding content |
| [[Media]] | Images and file attachments stored alongside content. |
| [[Activity & Integrations]] | What happened and who should hear about it |
| [[Export & Import]] | Getting content out as HTML, PDF or ZIP, and bringing ZIP exports back in. |
| [[API & Theming]] | The REST API and the theme system that customises the instance. |

## The journeys

A module tells you what one thing does. A flow tells you what actually happens to a customer, an order or a payment, start to finish. One note per journey in `3 Flows`. List them here.

- [[Editing a page]] — A user saves a page
- [[Logging in with single sign-on]] — An identity provider vouches for the user
- [[Exporting a book]] — A reader asks for a book as HTML, PDF or ZIP

## The mechanics

Conventions every module inherits, and traps that have bitten more than once. One note each in `5 Platform`. Read these before writing code; most review comments turn out to be one of them.

[[Permission evaluation]] · [[Entity hierarchy]]

## Why it's like that

Decisions worth remembering, above all the ones that surprise newcomers: reversals, rulings from the client, refactors that were deliberately deferred. The full list lives in `6 Decisions`. Put the ones that catch people out here.

- [[Side effects hang off the activity log]] — Notifications and webhooks are triggered from ActivityLogger::add(), not from the repositories that change content.

## Reading the graph

Open the graph view. Colours come from query patterns on the frontmatter, not from folders.

| Colour | What it means |
|---|---|
| 🟠 Orange | A module, written up |
| ⚫ Slate | A note nobody has written up yet — `depth: stub` |
| 🔴 Dark red | Deprecated — don't build on it |
| 🌸 Pink | Domain |
| 🟢 Green | Flow |
| 🔵 Blue | Integration |
| 🟣 Purple | Platform convention or trap |
| 🟡 Yellow | Decision |
| ⚪ Grey | Release |
| 🩵 Teal | Repo |

Because the groups are queries, a note turns slate the moment its `depth` says `stub` and orange when it is written up. The graph shows coverage without anyone maintaining a list.

## Views

Obsidian Bases over the frontmatter, in `_meta/views`. They read the notes live; nothing to regenerate.

- [[Coverage.base|Coverage]] — every note by `type` and `depth`, so you can see what is still a stub
- [[Stale.base|Stale]] — notes whose `updated` is older than `stale_days` in `vault.json`
- [[Recent.base|Recent]] — what changed in the vault lately
- [[Decisions.base|Decisions]] — every decision with its status, open ones first

## Honesty

This vault is only worth what it is worth if it is true. Each note records what was true when it was last `updated`. If the code disagrees, the code wins and the note gets fixed. `status: shipped` means the code is on the production branch named in `vault.json`; anything else is `in-progress`, `planned` or `deprecated`. `depth: stub` means the note is thin, not that the module is small. [[Coverage]] counts the stubs, [[Attention]] lists what needs a human, and [[Vault Changelog]] shows what the vault itself learned and when.
