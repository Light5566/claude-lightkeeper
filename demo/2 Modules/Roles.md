---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Access & Permissions
updated: 2026-10-18
tags: [module, domain/access-permissions]
---
# Roles

## What it is

A role bundles system permissions (manage settings, manage users) with default content permissions. Every user has one or more roles.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Users/Controllers/RoleController.php`, `app/Users/Controllers/RoleApiController.php` |
| Model | `app/Users/Models/Role.php` |
| Role permissions | `app/Permissions/Models/RolePermission.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Access & Permissions]] — this module's business area
- [[Users]] — a user's access is the union of their roles
- [[Entity Permissions]] — per-entity overrides are expressed per role

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
