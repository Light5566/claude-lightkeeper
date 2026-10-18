---
type: flow
status: shipped
depth: full
repo: BookStack
updated: 2026-10-18
tags: [flow]
---
# Editing a page

## What happens

A user saves a page. The save stores a revision, logs the activity, updates cross-links, and the activity fan-out notifies watchers and fires webhooks.

## Steps

| # | Step | Where | Module |
|---|---|---|---|
| 1 | PageController receives the form | `PageController::update` | [[Pages]] |
| 2 | PageRepo updates the page | `PageRepo::update` | [[Pages]] |
| 3 | the previous content becomes a revision | `RevisionRepo::storeNewForPage` | [[Page Revisions]] |
| 4 | cross-links are rewritten | `ReferenceUpdater` | [[References]] |
| 5 | the action is logged | `Activity::add` | [[Activity Log]] |
| 6 | watchers are notified | `ActivityLogger::setNotification` | [[Watching & Notifications]] |
| 7 | webhooks are queued | `ActivityLogger::dispatchWebhooks` | [[Webhooks]] |

## Modules crossed

- [[Pages]] — PageController receives the form
- [[Page Revisions]] — the previous content becomes a revision
- [[References]] — cross-links are rewritten
- [[Activity Log]] — the action is logged
- [[Watching & Notifications]] — watchers are notified
- [[Webhooks]] — webhooks are queued

## Where it breaks

- The side effects hang off the activity log, so a page saved any other way (API, import) gets the same fan-out only if it logs an activity.
