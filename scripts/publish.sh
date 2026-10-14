#!/usr/bin/env bash
# Run explicitly from your own authenticated machine. No remote changes in this release.
set -euo pipefail
cd "$(dirname "$0")/.."
owner="KyleJKistner"
name="LeanDigest"
visibility="${1:---private}"
case "$visibility" in --private|--public) ;; *) echo "Usage: scripts/publish.sh [--private|--public]" >&2; exit 2;; esac
command -v gh >/dev/null || { echo 'Install and authenticate GitHub CLI before publishing.' >&2; exit 2; }
actual="$(gh api user --jq .login)"
[[ "$actual" == "$owner" ]] || { echo "Authenticated GitHub account is $actual, not $owner. No changes made." >&2; exit 2; }
[[ -d .git ]] || git init -b main
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  git add .
  git commit -m 'Lean ProofReader 0.3.0; substantial source-bound reader and exact arithmetic certificates'
fi
[[ -z "$(git status --porcelain)" ]] || { echo 'Commit or stash changes before publishing.' >&2; exit 2; }
if git remote get-url origin >/dev/null 2>&1; then
  echo 'An origin already exists. Inspect it and publish manually; no existing remote was modified.' >&2
  exit 2
fi
# Creation fails rather than reusing/overwriting an existing remote repository.
gh repo create "$owner/$name" "$visibility" --source=. --remote=origin --push \
  --description 'Deterministic Lean proof-reading views with explicit evidence and corpus coverage gates'
