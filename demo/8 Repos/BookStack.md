---
type: repo
status: shipped
depth: full
repo: BookStack
updated: 2026-10-18
tags: [repo]
---
# BookStack

## What it is

BookStack is an open-source wiki platform (MIT) organised as shelves, books, chapters and pages. This vault is a demo map of its codebase, seeded from the directory structure and verified against the code where a note claims a call.

## Where it lives

`github.com/BookStackApp/BookStack`, a Laravel application: controllers, repos and models grouped by area under `app/`, routes in `routes/web.php` and `routes/api.php`, Blade views under `resources/views`.

## How it works

Each area under `app/` (Entities, Access, Permissions, Search, Activity, Uploads, Exports, Api, Theming) is one or more modules in this vault. Business logic sits in `*Repo` and `*Service` classes; controllers stay thin.

## Connects to

- [[Home]] — the entry page lists the domains
- [[Entity hierarchy]] — the base model every content type shares
- [[Permission evaluation]] — how visibility is decided

## Gotchas

- The `version` file is the running version; the changelog lives in the project's release notes, not in the repo.
