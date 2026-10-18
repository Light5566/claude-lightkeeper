---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Media
updated: 2026-10-18
tags: [module, domain/media]
---
# Images

## What it is

Uploaded images for pages, galleries, covers, avatars and diagrams, resized on demand and stored on a configurable disk.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Uploads/Controllers/ImageController.php`, `app/Uploads/Controllers/GalleryImageController.php`, `app/Uploads/Controllers/DrawioImageController.php` |
| Service | `app/Uploads/ImageService.php`, `app/Uploads/ImageRepo.php`, `app/Uploads/ImageResizer.php` |
| Storage | `app/Uploads/ImageStorage.php`, `app/Uploads/ImageStorageDisk.php` |
| Model | `app/Uploads/Image.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Media]] — this module's business area
- [[Pages]] — page content embeds gallery images
- [[Attachments]] — both share the storage abstraction

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
