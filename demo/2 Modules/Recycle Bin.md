---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Content
updated: 2026-10-18
tags: [module, domain/content]
---
# Recycle Bin

## What it is

Deleted shelves, books, chapters and pages go to the recycle bin first, where they can be restored or destroyed for good.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Entities/Controllers/RecycleBinController.php`, `app/Entities/Controllers/RecycleBinApiController.php` |
| Repo | `app/Entities/Repos/DeletionRepo.php` |
| Tools | `app/Entities/Tools/TrashCan.php` |
| Model | `app/Entities/Models/Deletion.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Content]] — this module's business area
- [[Pages]] — a deleted page is a Deletion record pointing at the soft-deleted page
- [[Books]] — deleting a book sends its whole contents to the bin

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
