---
type: platform
status: shipped
depth: full
repo: BookStack
updated: 2026-10-18
tags: [platform]
---
# Entity hierarchy

## What it is

Bookshelf, Book, Chapter and Page share one Entity base model with slugs, ownership and soft deletion; BookChild marks the levels that live inside a book. Most tools (cloner, parent changer, slug generator) are written once against Entity.

## Connects to

- [[Books]] — a Book is a container Entity
- [[Pages]] — a Page is a BookChild Entity
- [[Recycle Bin]] — soft deletion is what makes the bin possible

## Gotchas

-
