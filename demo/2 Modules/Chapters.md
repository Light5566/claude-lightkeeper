---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Content
updated: 2026-10-18
tags: [module, domain/content]
---
# Chapters

## What it is

A chapter groups pages inside a book. It is optional: pages can live directly under a book.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Entities/Controllers/ChapterController.php`, `app/Entities/Controllers/ChapterApiController.php` |
| Repo | `app/Entities/Repos/ChapterRepo.php` |
| Model | `app/Entities/Models/Chapter.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Content]] — this module's business area
- [[Books]] — a chapter always belongs to one book
- [[Pages]] — pages inside a chapter are ordered within it

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
