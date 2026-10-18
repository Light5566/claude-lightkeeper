---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Activity & Integrations
updated: 2026-10-18
tags: [module, domain/activity-integrations]
---
# Watching & Notifications

## What it is

Users watch a shelf, book, chapter or page at a chosen level and get emailed about updates and comments.

## Where it lives

| Surface | Path |
|---|---|
| Controller | `app/Activity/Controllers/WatchController.php` |
| Levels | `app/Activity/WatchLevels.php` |
| Tools | `app/Activity/Tools/EntityWatchers.php`, `app/Activity/Tools/UserEntityWatchOptions.php` |
| Notifications | `app/Activity/Notifications/NotificationManager.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Activity & Integrations]] — this module's business area
- [[Activity Log]] — ActivityLogger hands every logged action to NotificationManager
- [[User Preferences]] — a user's notification preferences gate the emails

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
