---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Activity & Integrations
updated: 2026-10-18
tags: [module, domain/activity-integrations]
---
# Webhooks

## What it is

Outgoing HTTP calls for chosen activity types, sent from a queued job.

## Where it lives

| Surface | Path |
|---|---|
| Controller | `app/Activity/Controllers/WebhookController.php` |
| Job | `app/Activity/DispatchWebhookJob.php` |
| Formatter | `app/Activity/Tools/WebhookFormatter.php` |
| Models | `app/Activity/Models/Webhook.php`, `app/Activity/Models/WebhookTrackedEvent.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Activity & Integrations]] — this module's business area
- [[Activity Log]] — a webhook fires from a logged activity, never directly

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
