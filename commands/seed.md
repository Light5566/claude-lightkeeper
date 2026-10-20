---
name: seed
description: Propose the first domains and module stubs for a fresh vault from the repo's navigation, route groups and top-level directories. Writes nothing until the user approves the list.
argument-hint: "[repo key] [--max N]"
---

Seed the vault from the code. `$ARGUMENTS` may name one repo key from `vault.json` and a cap on the number of stubs. The default is every watched repo and 60 stubs.

1. **Resolve the vault.** Run `vault status`. It prints the vault root, the repos it watches and their checkouts. If it fails, tell the user to run `/lightkeeper:init` first and stop.
2. **Read the shape of each repo.** Look at where the product groups things: the navigation menu, the route files and their groups, the top-level directories under the watched paths, the controller, service and model folders. Don't read every file. You want the clusters.
3. **Propose domains.** One `1 Domains/` note per navigation or route group. Name them the way the product does. Don't invent a parallel taxonomy.
4. **Propose module stubs**, at most 60, one per service, controller or model cluster that a user could point at in the UI or the API. For each, draft from `_templates/Module.md`:
   - `depth: stub`; `status: shipped` only if the checkout is on the production branch (`production_ref` in `vault.json`), otherwise `in-progress`;
   - `repo` set to the repo key, `domain` to its domain, `updated` to today;
   - **real *Where it lives* rows** from files that exist. Check each path exists before writing it. Fully qualify the first path in a cell. Never a container directory. Delete rows you can't fill;
   - *What it is* in two plain sentences from what the code clearly does, nothing more;
   - exactly one reasoned link to its domain in *Connects to*, and the reverse link in the domain note.
5. **Propose an `8 Repos/<repo key>.md` note** per repo: what the repo is, how it is laid out, how to run it, its production branch, where its changelog is.
6. **Show the proposed list**: domains first, then stubs grouped by domain with the files each one claims. **Ask before writing.** Drop or rename whatever the user says.
7. Write the approved notes, then run:

```bash
vault check --write
```

Fix everything it reports (unresolved links, container directories, alias collisions) and run it again until it exits 0. Commit the vault:

```bash
git -C <vault> add -A && git commit -m "seed: <N> domains, <M> module stubs, 8 Repos/<repo key>"
```

Remind the user that every stub is thin by design. They fill in as the team touches each module.
