#!/usr/bin/env bash
# Self-test for claude-vault: scaffolds a throwaway vault against a throwaway
# git repo, runs every hook with synthetic payloads and checks the CLIs.
# Needs only python3 and git. Run: bash check.sh
set -u
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
export CLAUDE_VAULTS_REGISTRY="$tmp/registry"
export TMPDIR="$tmp"
export VAULT_WINDOW_HOURS=6
unset VAULT_ROOT
fail=0
ok()   { echo "ok   $1"; }
bad()  { echo "FAIL $1: ${2:0:160}"; fail=1; }
expect_in() { if grep -q "$2" <<<"$3"; then ok "$1"; else bad "$1" "$3"; fi; }
expect_silent() { if [ -z "$3" ]; then ok "$1"; else bad "$1" "$3"; fi; }

# --- a fake project (Laravel-shaped so the preset path is exercised)
repo="$tmp/repo"; mkdir -p "$repo/app/Services" "$repo/routes"
git init -q -b main "$repo"; git -C "$repo" config user.email t@example.com; git -C "$repo" config user.name t
git -C "$repo" remote add origin git@github.com:acme/shop.git
touch "$repo/artisan"; echo "<?php class PaymentService {}" > "$repo/app/Services/PaymentService.php"
echo "<?php" > "$repo/routes/web.php"; echo "# shop" > "$repo/CHANGELOG.md"
git -C "$repo" add -A; git -C "$repo" commit -q -m "init"
other="$tmp/other"; git init -q -b main "$other"; git -C "$other" remote add origin https://github.com/acme/other.git

# --- init
out=$(python3 "$here/lib/init.py" "$tmp/vault" --name Shop --repo "$repo" --no-git 2>&1)
expect_in "init creates the vault" "created" "$out"
[ -f "$tmp/vault/_meta/vault.json" ] && ok "vault.json written" || bad "vault.json written" "$out"
grep -q '"remote": "github.com/acme/shop"' "$tmp/vault/_meta/vault.json" && ok "remote normalized" || bad "remote normalized" "$(cat "$tmp/vault/_meta/vault.json")"
grep -q '"watched"' "$tmp/vault/_meta/vault.json" && ok "watched detected" || bad "watched detected" ""
grep -q "$tmp/vault" "$CLAUDE_VAULTS_REGISTRY" && ok "registered" || bad "registered" "$(cat "$CLAUDE_VAULTS_REGISTRY")"

# --- one real module note + one stub
cat > "$tmp/vault/2 Modules/Payment.md" <<'MD'
---
type: module
aliases: [Checkout Payment]
status: shipped
depth: full
repo: repo
domain: Billing
updated: 2026-01-01
flags: [FEATURE_X_ENABLED]
tags: [module]
---

# Payment

## What it is

Takes the money for an order.

## Where it lives

| Surface | Path |
|---|---|
| Service | `app/Services/PaymentService.php` |
| Routes | `routes/web.php` |

## How it works

Calls the gateway.

## Connects to

- [[Order]] — a paid order moves to fulfilment

## Gotchas

- The gateway times out after 30 s.
MD
cat > "$tmp/vault/2 Modules/Order.md" <<'MD'
---
type: module
status: shipped
depth: stub
repo: repo
domain: Billing
updated: 2026-01-01
tags: [module]
---

# Order

## What it is

An order.

## Where it lives

| Surface | Path |
|---|---|
| Routes | `routes/orders.php` |

## Connects to

- [[Payment]] — paid through it
MD

# --- CLIs against the vault
out=$(python3 "$here/lib/check.py" --vault "$tmp/vault" --write 2>&1); rc=$?
[ $rc -eq 0 ] && ok "check --write exits 0" || bad "check --write exits 0" "$out"
[ -f "$tmp/vault/_meta/index.json" ] && ok "index written" || bad "index written" ""
out=$(cd "$repo" && python3 "$here/lib/find.py" --paths app/Services/PaymentService.php 2>&1)
expect_in "find --paths from the checkout resolves the vault via registry" "Payment" "$out"
out=$(cd "$repo" && python3 "$here/lib/find.py" gateway 2>&1)
expect_in "find content match offers an alias" "aliases: \[gateway\]" "$out"
out=$(cd "$tmp" && python3 "$here/lib/find.py" anything 2>&1); rc=$?
[ $rc -ne 0 ] && expect_in "find outside any vault explains" "no vault covers" "$out" || bad "find outside any vault explains" "$out"
echo "x@acme-corp.com" >> "$tmp/vault/2 Modules/Order.md"
out=$(python3 "$here/lib/check.py" --vault "$tmp/vault" 2>&1); rc=$?
[ $rc -ne 0 ] && expect_in "secrets rule catches an email" "email address" "$out" || bad "secrets rule catches an email" "$out"
sed -i.bak '/x@acme-corp.com/d' "$tmp/vault/2 Modules/Order.md"; rm -f "$tmp/vault/2 Modules/Order.md.bak"
python3 "$here/lib/check.py" --vault "$tmp/vault" --write >/dev/null 2>&1

# --- attention signals (Payment: stale + churn -> re-verify; Order: routes/orders.php -> path rot)
for i in 1 2 3 4 5; do echo "// c$i" >> "$repo/app/Services/PaymentService.php"; git -C "$repo" commit -q -am "change $i"; done
sed -i.bak 's/^updated: 2026-01-01/updated: 2025-01-01/' "$tmp/vault/2 Modules/Payment.md"; rm -f "$tmp/vault/2 Modules/Payment.md.bak"
out=$(python3 "$here/lib/check.py" --vault "$tmp/vault" --write 2>&1)
att=$(cat "$tmp/vault/_meta/Attention.md")
expect_in "re-verify signal (stale while code moved)" "re-verify.*Payment" "$att"
expect_in "path rot signal (claimed path missing)" "path rot.*Order" "$att"
expect_in "status.json carries the count" '"count": 2' "$(cat "$tmp/vault/_meta/status.json")"
expect_in "vault status prints attention" "attention: 2" "$(python3 "$here/lib/status.py" --vault "$tmp/vault" 2>&1)"
[ -f "$tmp/vault/_meta/Changelog.md" ] && ok "Changelog written" || bad "Changelog written" ""
[ -f "$tmp/vault/World.canvas" ] && python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$tmp/vault/World.canvas" && ok "World.canvas is valid JSON" || bad "World.canvas is valid JSON" ""

# --- hooks (run.py with synthetic payloads, project = the fake checkout)
# hook <name> key=value ...   builds the JSON payload in python (no nested shell quoting);
# file_path=... becomes tool_input; HOOK_PROJECT overrides the project dir.
hook() {
  local name="$1"; shift
  python3 -c '
import json, sys
d = {}
for a in sys.argv[1:]:
    k, _, v = a.partition("="); d[k] = v
if "file_path" in d:
    d["tool_name"] = "Edit"; d["tool_input"] = {"file_path": d.pop("file_path")}
print(json.dumps(d))' "$@" | CLAUDE_PROJECT_DIR="${HOOK_PROJECT:-$repo}" python3 "$here/lib/hooks/run.py" "$name" 2>&1
}
sid="sess-$RANDOM"
expect_in "primer on startup" "retrieval layer" "$(hook session_start source=startup cwd=$repo session_id=$sid)"
expect_silent "silent on resume" "" "$(hook session_start source=resume cwd=$repo session_id=$sid)"
expect_in "post-compaction reminder" "compacted" "$(hook session_start source=compact cwd=$repo session_id=$sid)"
expect_in "prompt hint matches a note name" "Payment" "$(hook prompt_hint "prompt=please fix the payment flow timeout" cwd=$repo session_id=$sid)"
expect_silent "same note not hinted twice" "" "$(hook prompt_hint "prompt=payment again please" cwd=$repo session_id=$sid)"
expect_in "decision nudge" "6 Decisions" "$(hook prompt_hint "prompt=the client said refunds go through support from now on" cwd=$repo session_id=$sid-d)"
expect_in "pre-edit pointer on an owned file" "documented by vault note" "$(hook file_guard file_path=$repo/app/Services/PaymentService.php cwd=$repo session_id=$sid-f)"
expect_in "stub wording on a stub's file" "still a stub" "$(hook file_guard file_path=$repo/routes/orders.php cwd=$repo session_id=$sid-f)"
expect_silent "no pointer for an unowned file" "" "$(hook file_guard file_path=$repo/README.md cwd=$repo session_id=$sid-f)"
echo "// change" >> "$repo/app/Services/PaymentService.php"
git -C "$tmp/vault" init -q 2>/dev/null; git -C "$tmp/vault" config user.email t@example.com; git -C "$tmp/vault" config user.name t
git -C "$tmp/vault" add -A >/dev/null; GIT_COMMITTER_DATE="2020-01-01T00:00:00" git -C "$tmp/vault" commit -q -m "seed" --date="2020-01-01T00:00:00" >/dev/null 2>&1 || true
expect_in "stop reminder names the note" "Affected notes: Payment" "$(hook stop_reminder cwd=$repo session_id=$sid-s)"
echo "- Another gotcha." >> "$tmp/vault/2 Modules/Payment.md"
expect_silent "stop reminder quiet when the vault is dirty" "" "$(hook stop_reminder cwd=$repo session_id=$sid-s2)"
expect_silent "silent for an uncovered repo" "" "$(HOOK_PROJECT=$other hook session_start source=startup cwd=$other)"
expect_silent "garbage payload is a no-op" "" "$(printf '%s' "not json" | CLAUDE_PROJECT_DIR="$repo" python3 "$here/lib/hooks/run.py" prompt_hint 2>&1)"

# --- launcher + log + sync
out=$(CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" log --vault "$tmp/vault" Payment 2>&1)
expect_in "vault log through the launcher" "Payment — 2 Modules/Payment.md" "$out"
out=$(cd "$repo" && CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" sync --no-fetch 2>&1)
expect_in "sync defaults to this checkout's target" "== repo ==" "$out"

# --- export + release
out=$(CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" export --vault "$tmp/vault" --out "$tmp/map.html" 2>&1)
grep -q "<html" "$tmp/map.html" 2>/dev/null && grep -q "Payment" "$tmp/map.html" && ok "vault export --html writes a page with the notes" || bad "vault export --html writes a page with the notes" "$out"
git -C "$repo" tag v0.1 "$(git -C "$repo" rev-list --max-parents=0 HEAD)"
out=$(cd "$repo" && CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" release v0.2 --json 2>&1)
expect_in "vault release finds the window since the previous tag" '"since": "v0.1"' "$out"
expect_in "vault release groups files by owning note" '"Payment"' "$out"
grep -q "{{" "$tmp/vault/Home.md" && bad "scaffold placeholders substituted" "$(grep -n '{{' "$tmp/vault/Home.md" | head -3)" || ok "scaffold placeholders substituted"

[ $fail -eq 0 ] && echo "all checks passed" || echo "SOME CHECKS FAILED"
exit $fail
