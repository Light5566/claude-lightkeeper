---
type: module
status: shipped
depth: stub
repo: BookStack
domain: Access & Permissions
updated: 2026-10-18
tags: [module, domain/access-permissions]
---
# Single Sign-on

## What it is

External identity: SAML2, OpenID Connect, LDAP and social providers. Each service maps the external identity to a user and can sync the provider's groups to roles.

## Where it lives

| Surface | Path |
|---|---|
| SAML2 | `app/Access/Saml2Service.php`, `app/Access/Controllers/Saml2Controller.php` |
| OIDC | `app/Access/Oidc/OidcService.php`, `app/Access/Controllers/OidcController.php` |
| LDAP | `app/Access/LdapService.php`, `app/Access/Ldap.php` |
| Social | `app/Access/SocialAuthService.php`, `app/Access/Controllers/SocialController.php` |
| Group sync | `app/Access/GroupSyncService.php` |

## How it works

_Stub: written up the first time someone works on this module for real._

## Connects to

- [[Access & Permissions]] — this module's business area
- [[Authentication]] — every SSO flow finishes through LoginService
- [[Roles]] — GroupSyncService maps external groups to roles
- [[Logging in with single sign-on]] — the end-to-end journey

## Config & flags

| Key | Default | Effect |
|---|---|---|

## Gotchas

-

## History

-
