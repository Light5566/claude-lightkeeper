---
type: module
status: shipped
depth: stub
repo: BookStack
domain: API & Theming
updated: 2026-10-18
tags: [module, domain/api-theming]
---
# REST API

## What it is

A token-authenticated REST API over the same controllers' API variants, with generated docs.

## Where it lives

| Surface | Path |
|---|---|
| Guard | `app/Api/ApiTokenGuard.php`, `app/Api/ApiToken.php` |
| Docs | `app/Api/ApiDocsController.php`, `app/Api/ApiDocsGenerator.php` |
| Tokens | `app/Api/UserApiTokenController.php` |
| Routes | `routes/api.php` |
| Listing | `app/Api/ListingResponseBuilder.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[API & Theming]] — this module's business area
- [[Users]] — API tokens belong to a user and carry its permissions

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
