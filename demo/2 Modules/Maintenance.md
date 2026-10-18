---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Users & Settings
updated: 2026-10-18
tags: [module, domain/users-settings]
---
# Maintenance

## What it is

Admin maintenance actions (cleanup, test email, regenerate references) and the status endpoint monitors poll.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Settings/MaintenanceController.php`, `app/Settings/StatusController.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Users & Settings]] — this module's business area
- [[Settings]] — maintenance lives under the settings area
- [[References]] — the regenerate-references action rebuilds cross-links

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
