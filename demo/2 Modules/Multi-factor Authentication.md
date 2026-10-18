---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Access & Permissions
updated: 2026-10-18
tags: [module, domain/access-permissions]
---
# Multi-factor Authentication

## What it is

Time-based one-time codes and backup codes as a second factor, which a role can require.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Access/Controllers/MfaController.php`, `app/Access/Controllers/MfaTotpController.php`, `app/Access/Controllers/MfaBackupCodesController.php` |
| Services | `app/Access/Mfa/TotpService.php`, `app/Access/Mfa/BackupCodeService.php`, `app/Access/Mfa/MfaSession.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Access & Permissions]] — this module's business area
- [[Authentication]] — the MFA challenge sits between credential check and session start

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
