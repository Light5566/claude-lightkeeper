---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Content
updated: 2026-10-18
tags: [module, domain/content]
---
# Bookshelves

## What it is

Shelves group books. A book can sit on several shelves, and a shelf can set the context readers navigate books in.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Entities/Controllers/BookshelfController.php`, `app/Entities/Controllers/BookshelfApiController.php` |
| Repo | `app/Entities/Repos/BookshelfRepo.php` |
| Model | `app/Entities/Models/Bookshelf.php` |
| Queries | `app/Entities/Queries/BookshelfQueries.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Content]] — this module's business area
- [[Books]] — a shelf is an ordered collection of books
- [[Entity Permissions]] — shelf permissions can be copied down to the books on it

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
