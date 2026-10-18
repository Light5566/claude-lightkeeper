# claude-vault PR notes action

Comments on every pull request with the knowledge-vault notes that own the files it changed, so the question "were the notes updated?" is asked by the repo, not by whoever remembers. It works for teammates who never open Claude Code.

It is **advisory only**: it posts or updates one comment, never fails the check, never blocks a merge, never writes to the vault.

## Wire it into a code repo

`.github/workflows/vault-notes.yml` in the code repository:

```yaml
name: vault notes
on:
  pull_request:
permissions:
  contents: read
  pull-requests: write
jobs:
  notes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0            # the action diffs base..head
      - uses: Light5566/claude-vault/action@main
        with:
          vault_repo: your-org/your-vault       # the vault's own repository
          vault_ref: main                       # optional
          vault_path: ""                        # optional: folder inside that repo
          vault_token: ${{ secrets.VAULT_TOKEN }}  # only for a private vault repo
```

For a private vault repository create a fine-grained personal access token with read access to that repository and store it as the `VAULT_TOKEN` secret. A public vault needs no token.

The vault's `_meta/vault.json` must list the code repository under `repos` with its `remote` (any URL form), exactly as it does for the hooks; that is how the action knows which `watched` directories and which notes apply.

## What it posts

```
### Knowledge vault: My App

Files in this PR belong to these vault notes. Were they updated?

| Note    | Updated    | Files |
|---------|------------|-------|
| Invoice | 2026-10-02 | `app/Services/InvoiceService.php`, `routes/web.php` |
| Refund  | 2026-09-28 | `app/Services/RefundCalculator.php` |

3 changed file(s) match no note (a new module, or an undocumented surface?):

- `app/Services/LoyaltyService.php`
- …
```

The comment carries a hidden marker, so a later push to the same PR updates it instead of adding another. Lock files, docs and other noise are skipped, using the same list `vault sync` uses.

## What it never does

- Fail the job or block a merge: every step is `continue-on-error`.
- Modify the vault or the code repository.
- Run anything but `git diff` and the plugin's own stdlib Python.

## Testing it without a PR

```bash
printf 'app/Services/InvoiceService.php\n' > /tmp/changed.txt
python3 action/pr_notes.py --vault ~/vaults/myapp --files /tmp/changed.txt --repo ~/code/myapp
```
