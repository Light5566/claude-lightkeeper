---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Content
updated: 2026-10-18
tags: [module, domain/content]
---
# Sort Rules

## What it is

Sort rules are reusable orderings (by name, date, type) that a book can apply automatically to its chapters and pages.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Sorting/SortRuleController.php`, `app/Sorting/BookSortController.php` |
| Sorter | `app/Sorting/BookSorter.php` |
| Model | `app/Sorting/SortRule.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Content]] — this module's business area
- [[Books]] — a book opts into a sort rule

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
