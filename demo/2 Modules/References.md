---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Search & References
updated: 2026-10-18
tags: [module, domain/search-references]
---
# References

## What it is

Cross-links between pages are stored so a page can list where it is referenced, and links are rewritten when a target moves.

## Where it lives

| Surface | Path |
|---|---|
| Controller | `app/References/ReferenceController.php` |
| Parser | `app/References/CrossLinkParser.php` |
| Store | `app/References/ReferenceStore.php`, `app/References/ReferenceUpdater.php`, `app/References/ReferenceFetcher.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Search & References]] — this module's business area
- [[Pages]] — PageRepo calls ReferenceUpdater on save

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
