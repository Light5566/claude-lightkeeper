#!/usr/bin/env bash
# Self-test for Lightkeeper: scaffolds a throwaway vault against a throwaway
# git repo, runs every hook with synthetic payloads and checks the CLIs.
# Needs only python3 and git. Run: bash check.sh
set -u
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
export CLAUDE_VAULTS_REGISTRY="$tmp/registry"
export TMPDIR="$tmp"
export VAULT_WINDOW_HOURS=6
unset VAULT_ROOT HERMES_HOME CLAUDE_VAULT_PLUGIN
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

# --- --git-hook leaves a foreign hook alone, even one that mentions claude-vault
printf '#!/bin/sh\n# someone else: ~/claude-vault-private/gate.sh\n' > "$repo/.git/hooks/pre-push"
out=$(python3 "$here/lib/init.py" --adopt "$tmp/vault" --name Shop --repo "$repo" --git-hook 2>&1)
grep -q "someone else" "$repo/.git/hooks/pre-push" && ok "foreign pre-push hook kept" || bad "foreign pre-push hook kept" "$out"
grep -q "claude-vault git hook body" "$repo/.git/hooks/post-merge" && ok "post-merge hook installed" || bad "post-merge hook installed" "$out"
rm -f "$repo/.git/hooks/pre-push" "$repo/.git/hooks/post-merge"

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
[ $rc -eq 0 ] && expect_in "secrets rule warns on an email" "email address" "$out" || bad "secrets rule warns on an email" "$out"
python3 "$here/lib/check.py" --vault "$tmp/vault" --strict >/dev/null 2>&1 && bad "secrets rule fails under --strict" "" || ok "secrets rule fails under --strict"
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
[ -f "$tmp/vault/_meta/Vault Changelog.md" ] && ok "Vault Changelog written" || bad "Vault Changelog written" ""
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
echo '{"accentColor": "#123456"}' > "$tmp/vault/.obsidian/appearance.json"; git -C "$tmp/vault" commit -qam "obsidian config" >/dev/null 2>&1
expect_in "an Obsidian-settings commit does not count as the vault moving" "Affected notes: Payment" "$(hook stop_reminder cwd=$repo session_id=$sid-s3)"
# --- Hermes adapter: the root __init__.py driven by a fake plugin context, no Hermes installed.
# It shares the hooks' per-session state, so the prompt test uses Payment and the edit tests use Order.
out=$(cd "$repo" && python3 - "$here" "$repo" <<'PY'
import importlib.util, json, os, sys
root, repo = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("lk_hermes", os.path.join(root, "__init__.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Ctx:  # the slice of Hermes's PluginContext the adapter touches
    def __init__(s): s.hooks, s.skills, s.desc = {}, {}, {}
    def register_hook(s, name, fn): s.hooks[name] = fn
    def register_skill(s, name, path, description=""): s.skills[name] = path; s.desc[name] = description
ctx = Ctx(); m.register(ctx); h = ctx.hooks
sid = "hermes-%d" % os.getpid()
def check(name, cond): print(("ok   " if cond else "FAIL ") + "hermes: " + name)
def llm(msg, first=False, s=sid):
    return h["pre_llm_call"](session_id=s, user_message=msg, conversation_history=[], is_first_turn=first, model="m", platform="cli")
def edit(tool, res, path, s=sid):
    return h["transform_tool_result"](tool_name=tool, args={"path": path}, result=res, task_id="t1", session_id=s)

r = llm("hi", first=True)
check("first-turn primer", bool(r) and "retrieval layer" in r["context"])
check("primer names the skills", bool(r) and "lightkeeper:knowledge-vault" in r["context"] and "lightkeeper:seed" in r["context"])
check("primer not repeated on the next model call", llm("hi", first=True) is None)
r = llm("please fix the payment flow timeout")
check("prompt hint names the note", bool(r) and "Payment" in r["context"])
check("same message, next model call: silent", llm("please fix the payment flow timeout") is None)
r = edit("write_file", json.dumps({"success": True}), "routes/orders.php")
check("relative path resolves against the session cwd", bool(r) and r.startswith('{"success": true}') and "still a stub" in r)
ok_res = json.dumps({"success": True, "resolved_path": repo + "/routes/orders.php", "files_modified": [repo + "/routes/orders.php"]})
check("patch on the same file: no second pointer", edit("patch", ok_res, "routes/orders.php") is None)
check("error result untouched", edit("write_file", '{"error": "no such file"}', "x.php") is None)
check("other tools untouched", h["transform_tool_result"](tool_name="terminal", args={"command": "ls"}, result="ok", task_id="t1") is None)
r = edit("write_file", json.dumps({"success": True, "resolved_path": repo + "/app/Services/PaymentService.php"}), "ignored.php", s=sid + "-2")
check("resolved_path wins and the session_id kwarg is used", bool(r) and "documented by vault note" in r)
r = h["pre_verify"](session_id=sid, platform="cli", model="m", coding=True, attempt=0, final_response="done", changed_paths=["app/Services/PaymentService.php"])
check("verify nudge names the note", bool(r) and r.get("action") == "continue" and "Affected notes: Payment" in r["message"] and "Act on this now" in r["message"])
check("no nudge on a retry", h["pre_verify"](session_id=sid, platform="cli", model="m", coding=True, attempt=1, final_response="done", changed_paths=["x"]) is None)
r = h["on_session_finalize"](session_id=sid, platform="cli")
check("session-end notice", bool(r) and "Knowledge vault not updated" in r["message"])
check("eight skills registered", set(ctx.skills) == {"knowledge-vault", "vault-sync", "vault-tidy", "init", "seed", "tidy", "trace", "release"})
check("every skill path exists with a description", all(os.path.isfile(p) and ctx.desc[n] for n, p in ctx.skills.items()))
gen = {c: open(ctx.skills[c]).read() for c in ("init", "seed", "tidy", "trace", "release")}
check("generated skills carry no Claude Code placeholders", not any("$ARGUMENTS" in t or "CLAUDE_PLUGIN_ROOT" in t for t in gen.values()))
check("generated init skill bakes the absolute plugin root", os.path.join(os.path.realpath(root), "lib", "init.py") in gen["init"])
PY
)
echo "$out"; grep -q "^FAIL" <<<"$out" && fail=1

echo "- Another gotcha." >> "$tmp/vault/2 Modules/Payment.md"
expect_silent "stop reminder quiet when the vault is dirty" "" "$(hook stop_reminder cwd=$repo session_id=$sid-s2)"
expect_silent "silent for an uncovered repo" "" "$(HOOK_PROJECT=$other hook session_start source=startup cwd=$other)"
expect_silent "garbage payload is a no-op" "" "$(printf '%s' "not json" | CLAUDE_PROJECT_DIR="$repo" python3 "$here/lib/hooks/run.py" prompt_hint 2>&1)"

# --- launcher + log + sync
out=$(CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" log --vault "$tmp/vault" Payment 2>&1)
expect_in "vault log through the launcher" "Payment — 2 Modules/Payment.md" "$out"
mkdir -p "$tmp/home/.hermes/plugins"; ln -s "$here" "$tmp/home/.hermes/plugins/lightkeeper"; cp "$here/bin/vault" "$tmp/vault-cli"
out=$(HOME="$tmp/home" python3 "$tmp/vault-cli" log --vault "$tmp/vault" Payment 2>&1)
expect_in "a copied launcher finds the plugin under ~/.hermes/plugins" "Payment — 2 Modules/Payment.md" "$out"
v=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$here/.claude-plugin/plugin.json")
grep -q "^version: \"$v\"$" "$here/plugin.yaml" && ok "plugin.yaml version matches plugin.json" || bad "plugin.yaml version matches plugin.json" "$v"
out=$(cd "$repo" && CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" sync --no-fetch 2>&1)
expect_in "sync defaults to this checkout's target" "== repo ==" "$out"

# --- export + release
out=$(CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" export --vault "$tmp/vault" --out "$tmp/map.html" 2>&1)
grep -q "<html" "$tmp/map.html" 2>/dev/null && grep -q "Payment" "$tmp/map.html" && ok "vault export --html writes a page with the notes" || bad "vault export --html writes a page with the notes" "$out"
out=$(cd "$repo" && CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" export --html "$tmp/map2.html" 2>&1)
grep -q "Payment" "$tmp/map2.html" 2>/dev/null && ok "vault export --html finds the vault from the cwd" || bad "vault export --html finds the vault from the cwd" "$out"
git -C "$repo" tag v0.1 "$(git -C "$repo" rev-list --max-parents=0 HEAD)"
out=$(cd "$repo" && CLAUDE_VAULT_PLUGIN="$here" python3 "$here/bin/vault" release v0.2 --json 2>&1)
expect_in "vault release finds the window since the previous tag" '"since": "v0.1"' "$out"
expect_in "vault release groups files by owning note" '"Payment"' "$out"
grep -q "{{" "$tmp/vault/Home.md" && bad "scaffold placeholders substituted" "$(grep -n '{{' "$tmp/vault/Home.md" | head -3)" || ok "scaffold placeholders substituted"
python3 -c "import json,sys; assert len(json.load(open(sys.argv[1]))['colorGroups']) >= 10" "$tmp/vault/.obsidian/graph.json" 2>/dev/null && ok "new vault gets the Obsidian graph colours" || bad "new vault gets the Obsidian graph colours" "$(ls -a "$tmp/vault/.obsidian" 2>&1)"

# --- PR notes action renderer
printf '%s\n' app/Services/PaymentService.php composer.lock app/Services/NewThing.php > "$tmp/changed.txt"
out=$(python3 "$here/action/pr_notes.py" --vault "$tmp/vault" --files "$tmp/changed.txt" --repo "$repo" 2>&1)
expect_in "pr_notes starts with the marker" "^<!-- claude-vault -->" "$out"
expect_in "pr_notes names the owning note" "\*\*Payment\*\*" "$out"
expect_in "pr_notes lists the unmatched file" "NewThing.php" "$out"
grep -q "composer.lock" <<<"$out" && bad "pr_notes skips noise files" "$out" || ok "pr_notes skips noise files"
out=$(python3 "$here/action/pr_notes.py" --vault "$tmp/nowhere" --files "$tmp/changed.txt" --repo "$repo" 2>&1); rc=$?
[ $rc -eq 0 ] && expect_in "pr_notes never fails without a vault" "Could not read the vault" "$out" || bad "pr_notes never fails without a vault" "$out"

[ $fail -eq 0 ] && echo "all checks passed" || echo "SOME CHECKS FAILED"
exit $fail
