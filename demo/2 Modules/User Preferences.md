---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Users & Settings
updated: 2026-10-18
tags: [module, domain/users-settings]
---
# User Preferences

## What it is

Per-user choices: language, dark mode, keyboard shortcuts, notification preferences and the user's own account settings.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Users/Controllers/UserPreferencesController.php`, `app/Users/Controllers/UserAccountController.php` |
| Stores | `app/Settings/UserNotificationPreferences.php`, `app/Settings/UserShortcutMap.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Users & Settings]] — this module's business area
- [[Users]] — preferences hang off the user record
- [[Watching & Notifications]] — notification preferences decide which activity emails a user

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
