---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Content
updated: 2026-10-18
tags: [module, domain/content]
---
# Books

## What it is

A book holds chapters and pages in order. It is the unit most permissions, exports and sort rules are applied to.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Entities/Controllers/BookController.php`, `app/Entities/Controllers/BookApiController.php` |
| Repo | `app/Entities/Repos/BookRepo.php` |
| Model | `app/Entities/Models/Book.php` |
| Contents | `app/Entities/Tools/BookContents.php` |
| Queries | `app/Entities/Queries/BookQueries.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Content]] — this module's business area
- [[Chapters]] — chapters are the book's optional middle level
- [[Pages]] — pages belong to a book, directly or through a chapter
- [[Sort Rules]] — a sort rule decides the order of a book's contents
- [[Exports]] — a book can be exported whole as HTML, PDF or ZIP

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
