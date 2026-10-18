---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Access & Permissions
updated: 2026-10-18
tags: [module, domain/access-permissions]
---
# Authentication

## What it is

Standard email-and-password login, registration, email confirmation and password reset. LoginService is the single place a session is started, which the SSO methods also go through.

## Where it lives

| Surface | Path |
|---|---|
| Controllers | `app/Access/Controllers/LoginController.php`, `app/Access/Controllers/RegisterController.php`, `app/Access/Controllers/ForgotPasswordController.php`, `app/Access/Controllers/ResetPasswordController.php` |
| Service | `app/Access/LoginService.php`, `app/Access/RegistrationService.php` |
| Guards | `app/Access/Guards` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Access & Permissions]] — this module's business area
- [[Multi-factor Authentication]] — a login can be held until an MFA challenge passes
- [[Single Sign-on]] — SAML2, OIDC, LDAP and social logins end in LoginService

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
