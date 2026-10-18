#!/usr/bin/env bash
# claude-vault git hook body (post-merge, pre-push): after a merge or before a
# push on this branch, say how far the knowledge vault is behind it. REPORT
# ONLY: writes nothing, moves no cursor, always exits 0 so git never fails here.
# Silent on machines without the vault or the `vault` launcher.
command -v vault >/dev/null 2>&1 || exit 0
branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null) || exit 0
[ -n "$branch" ] || exit 0
vault sync --brief --no-fetch --ref "$branch" 2>/dev/null || true
exit 0
