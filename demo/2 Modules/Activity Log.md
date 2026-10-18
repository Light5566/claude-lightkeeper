---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Activity & Integrations
updated: 2026-10-18
tags: [module, domain/activity-integrations]
---
# Activity Log

## What it is

One row per action anything in the system takes. Logging an activity is also what triggers notifications and webhooks.

## Where it lives

| Surface | Path |
|---|---|
| Logger | `app/Activity/Tools/ActivityLogger.php` |
| Types | `app/Activity/ActivityType.php` |
| Model | `app/Activity/Models/Activity.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Activity & Integrations]] — this module's business area
- [[Watching & Notifications]] — ActivityLogger::add() calls setNotification()
- [[Webhooks]] — ActivityLogger::add() calls dispatchWebhooks()
- [[Audit Log]] — the admin listing reads this table

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
