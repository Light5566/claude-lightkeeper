---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Users & Settings
updated: 2026-10-18
tags: [module, domain/users-settings]
---
# Settings

## What it is

Instance-wide settings: name, branding, registration, features. Stored in the database and read through one service.

## Where it lives

| Surface | Path |
|---|---|
| Controller | `app/Settings/SettingController.php` |
| Service | `app/Settings/SettingService.php`, `app/Settings/AppSettingsStore.php` |
| Model | `app/Settings/Setting.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Users & Settings]] — this module's business area
- [[Theme System]] — custom head content and theme settings are read alongside settings

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
