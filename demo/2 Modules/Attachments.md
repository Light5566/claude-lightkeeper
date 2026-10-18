---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Media
updated: 2026-10-18
tags: [module, domain/media]
---
# Attachments

## What it is

Files or links attached to a page, served with the page's permissions.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Uploads/Controllers/AttachmentController.php`, `app/Uploads/Controllers/AttachmentApiController.php` |
| Service | `app/Uploads/AttachmentService.php` |
| Model | `app/Uploads/Attachment.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Media]] — this module's business area
- [[Pages]] — an attachment belongs to one page
- [[Entity Permissions]] — downloading an attachment checks the page's permission

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
