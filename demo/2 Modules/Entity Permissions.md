---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Access & Permissions
updated: 2026-10-18
tags: [module, domain/access-permissions]
---
# Entity Permissions

## What it is

Per-shelf, book, chapter or page overrides of what each role may view, create, update or delete. They are flattened into joint permissions so listing and search can filter in SQL.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Permissions/PermissionsController.php`, `app/Permissions/ContentPermissionApiController.php` |
| Repo | `app/Permissions/PermissionsRepo.php` |
| Builder | `app/Permissions/JointPermissionBuilder.php` |
| Applicator | `app/Permissions/PermissionApplicator.php` |
| Models | `app/Permissions/Models/EntityPermission.php`, `app/Permissions/Models/JointPermission.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Access & Permissions]] — this module's business area
- [[Roles]] — entity permissions are granted per role
- [[Permission evaluation]] — how overrides become the joint_permissions rows every query reads

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
