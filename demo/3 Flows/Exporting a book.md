---
type: flow
status: shipped
depth: full
repo: BookStack
updated: 2026-10-18
tags: [flow]
---
# Exporting a book

## What happens

A reader asks for a book as HTML, PDF or ZIP. The formatter walks the book's chapters and pages and renders them into one contained document.

## Steps

| # | Step | Where | Module |
|---|---|---|---|
| 1 | the request arrives | `BookExportController` | [[Exports]] |
| 2 | the book's contents are walked | `ExportFormatter::bookToContainedHtml` | [[Books]] |
| 3 | PDF is rendered from that HTML | `PdfGenerator` | [[Exports]] |
| 4 | ZIP bundles content plus images and attachments | `ZipExportBuilder` | [[Exports]] |

## Modules crossed

- [[Exports]] — the request arrives
- [[Books]] — the book's contents are walked

## Where it breaks

- The export respects the reader's permissions: pages the reader cannot see are left out, so two users can get different PDFs of the same book.
