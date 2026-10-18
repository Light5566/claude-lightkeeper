---
type: decision
status: accepted
date: 2026-10-18
updated: 2026-10-18
tags: [decision]
---
# Side effects hang off the activity log

## Decision

Notifications and webhooks are triggered from ActivityLogger::add(), not from the repositories that change content.

## Context

Observed in the code while seeding this vault; reason not recorded by the project itself.

## Why this and not the alternative

Every content change already logs an activity for the audit trail; reusing that single point means a new activity type gets notifications and webhooks for free, and an unlogged change gets neither.

## Consequences

A content change made without logging an activity produces no notification and no webhook.

## Affects

- [[Activity Log]] — the single fan-out point
- [[Webhooks]] — fired from the logger
- [[Watching & Notifications]] — notified from the logger
