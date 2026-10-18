---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Export & Import
updated: 2026-10-18
tags: [module, domain/export-import]
---
# Import

## What it is

A ZIP export from any BookStack instance can be uploaded, validated and imported as new content.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Exports/Controllers/ImportController.php`, `app/Exports/Controllers/ImportApiController.php` |
| Runner | `app/Exports/ZipExports/ZipImportRunner.php`, `app/Exports/ZipExports/ZipExportReader.php` |
| Repo | `app/Exports/ImportRepo.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Export & Import]] — this module's business area
- [[Exports]] — import understands the ZIP export format

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
