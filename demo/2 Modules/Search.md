---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Search & References
updated: 2026-10-18
tags: [module, domain/search-references]
---
# Search

## What it is

Full-text search over all content with filters and term syntax. The index is a table of weighted terms per entity, rebuilt whenever content changes.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Search/SearchController.php`, `app/Search/SearchApiController.php` |
| Runner | `app/Search/SearchRunner.php` |
| Index | `app/Search/SearchIndex.php`, `app/Search/SearchTerm.php`, `app/Search/SearchTextTokenizer.php` |
| Options | `app/Search/SearchOptions.php`, `app/Search/SearchOptionSet.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Search & References]] — this module's business area
- [[Pages]] — page content is tokenised into search terms
- [[Entity Permissions]] — results are filtered by the joint permissions of the current user

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
