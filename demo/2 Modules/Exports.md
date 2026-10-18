---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Export & Import
updated: 2026-10-18
tags: [module, domain/export-import]
---
# Exports

## What it is

Any page, chapter or book can be exported as contained HTML, plain text, PDF or a portable ZIP.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Exports/Controllers/BookExportController.php`, `app/Exports/Controllers/ChapterExportController.php`, `app/Exports/Controllers/PageExportController.php` |
| Formatter | `app/Exports/ExportFormatter.php` |
| PDF | `app/Exports/PdfGenerator.php` |
| ZIP | `app/Exports/ZipExports/ZipExportBuilder.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Export & Import]] — this module's business area
- [[Books]] — ExportFormatter::bookToContainedHtml() walks the book's contents
- [[Import]] — the ZIP format is what import reads back
- [[Exporting a book]] — the end-to-end journey

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
