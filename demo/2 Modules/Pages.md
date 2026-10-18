---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Content
updated: 2026-10-18
tags: [module, domain/content]
---
# Pages

## What it is

A page is the document people read and edit, in the WYSIWYG or markdown editor. Saving a page is where most of the system's side effects start.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Entities/Controllers/PageController.php`, `app/Entities/Controllers/PageApiController.php` |
| Repo | `app/Entities/Repos/PageRepo.php` |
| Model | `app/Entities/Models/Page.php` |
| Content tools | `app/Entities/Tools/PageContent.php`, `app/Entities/Tools/PageEditorData.php`, `app/Entities/Tools/PageIncludeParser.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Content]] — this module's business area
- [[Page Revisions]] — every save stores a revision through RevisionRepo::storeNewForPage()
- [[Activity Log]] — PageRepo records PAGE_UPDATE through Activity::add()
- [[References]] — ReferenceUpdater rewrites cross-links when a page changes
- [[Editing a page]] — the end-to-end journey of a save

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
