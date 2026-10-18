---
type: platform
status: shipped
depth: full
repo: BookStack
updated: 2026-10-18
tags: [platform]
---
# Permission evaluation

## What it is

Entity permissions are flattened into a joint_permissions table by JointPermissionBuilder, and PermissionApplicator::restrictEntityQuery() joins that table into every content query, so visibility is decided in SQL rather than per row in PHP.

## Connects to

- [[Entity Permissions]] — the overrides that get flattened
- [[Search]] — search results go through the same query restriction

## Gotchas

-
