#!/bin/sh
# Mirror this working tree (committed or not) to the Linux build host. Only changed objects travel.
# usage: sh tools-sync.sh [remote, default "legion"]
set -e
cd "$(dirname "$0")/.."
R=${1:-legion}
export GIT_INDEX_FILE=.git/wip-index
cp -f .git/index "$GIT_INDEX_FILE" 2>/dev/null || true
git add -A
C=$(git commit-tree "$(git write-tree)" -p HEAD -m wip)
unset GIT_INDEX_FILE
git push -q -f "$R" "$C:refs/heads/wip"
ssh -o BatchMode=yes "$(git remote get-url "$R" | cut -d: -f1)" "cd $(git remote get-url "$R" | cut -d: -f2) && git checkout -q -f --detach wip && git clean -q -fd"
