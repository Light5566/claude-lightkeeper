---
type: flow
status: shipped
depth: full
repo: BookStack
updated: 2026-10-18
tags: [flow]
---
# Logging in with single sign-on

## What happens

An identity provider vouches for the user. The matching service maps the identity to a user, syncs groups to roles, and starts the session through the same LoginService as a password login.

## Steps

| # | Step | Where | Module |
|---|---|---|---|
| 1 | the provider redirects back | `Saml2Controller / OidcController` | [[Single Sign-on]] |
| 2 | the service validates the response | `Saml2Service / OidcService` | [[Single Sign-on]] |
| 3 | external groups become roles | `GroupSyncService` | [[Roles]] |
| 4 | the session starts | `LoginService` | [[Authentication]] |

## Modules crossed

- [[Single Sign-on]] — the provider redirects back
- [[Roles]] — external groups become roles
- [[Authentication]] — the session starts

## Where it breaks

- Group sync only runs when the provider's group attribute is configured; without it the user keeps the roles an admin set.
