---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Content
updated: 2026-10-18
tags: [module, domain/content]
---
# Page Revisions

## What it is

Every page save keeps the previous content as a revision, and drafts are revisions too. Readers can view, compare and restore them.

## Where it lives

| Surface | Path |
|---|---|
| Controller | `app/Entities/Controllers/PageRevisionController.php` |
| Repo | `app/Entities/Repos/RevisionRepo.php` |
| Model | `app/Entities/Models/PageRevision.php` |
| Queries | `app/Entities/Queries/PageRevisionQueries.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Content]] — this module's business area
- [[Pages]] — revisions are the history of one page

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
