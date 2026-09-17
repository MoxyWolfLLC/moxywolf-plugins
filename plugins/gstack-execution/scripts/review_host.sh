#!/usr/bin/env bash
# XE-009: stand up a review host — a shell whose background processes survive between calls.
#
# Why this exists. peer_review dispatches a reviewer and collects it later (XE-004), which only
# works where a detached process outlives the call that started it. Cowork's device_bash does not
# qualify: every call is capped (120s observed 2026-09-17) and gets its own PID namespace, torn
# down on return, so a dispatched review is reaped before it writes anything. Three reviews died
# that way in one session. The same class of failure is recorded in the vault from 2026-06-13,
# where a reasoning model tripped a 45s sandbox cap; the fix then and now is to move the shell, not
# to pick a faster model, because lowering the reviewer floor to fit the clock buys a pass rather
# than earning one.
#
# Run this in a persistent shell (the Cowork cloud container, or any host with a durable session).
# It is idempotent: re-running updates the checkout and skips an install that is already present.
#
# ponytail: a shell script, not a provisioning system. It installs one CLI and clones one repo.
# If this ever needs a second host or a second reviewer, that is the point to reach for something
# bigger -- not before.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/MoxyWolfLLC/moxywolf-plugins.git}"
REF="${1:-main}"
WORK="${REVIEW_HOST_WORK:-$HOME/review-host}"
CREDS="${REVIEW_HOST_CREDS:-/mnt/user-data/uploads/MoxyWolf Vault/_Shared Knowledge/Agents and Plugins}"
export NPM_CONFIG_PREFIX="${NPM_CONFIG_PREFIX:-$HOME/.npm-global}"
export PATH="$NPM_CONFIG_PREFIX/bin:$PATH"

say() { printf '  %s\n' "$*"; }

# --- credentials -------------------------------------------------------------------------------
# Read from files, never from arguments or the environment of a logged command: a secret passed as
# an argument shows up in ps and in shell history.
[ -d "$CREDS" ] || { echo "no credentials directory at $CREDS" >&2
                     echo "stage the vault's github-pat.env and gemini.env there first" >&2; exit 2; }
GITHUB_PAT=$(grep -m1 '^GITHUB_PAT=' "$CREDS/github-pat.env" | cut -d= -f2- | tr -d '"'\'' \r\n')
GEMINI_API_KEY=$(grep -m1 '^GOOGLE_GEMINI_API_KEY=' "$CREDS/gemini.env" | cut -d= -f2- | tr -d '"'\'' \r\n')
[ -n "$GITHUB_PAT" ] || { echo "GITHUB_PAT empty in $CREDS/github-pat.env" >&2; exit 2; }
[ -n "$GEMINI_API_KEY" ] || { echo "GOOGLE_GEMINI_API_KEY empty in $CREDS/gemini.env" >&2; exit 2; }
export GEMINI_API_KEY
AUTH="Authorization: Basic $(printf 'x-access-token:%s' "$GITHUB_PAT" | base64 | tr -d '\n')"
say "credentials loaded from $CREDS"

# --- reviewer CLI ------------------------------------------------------------------------------
if command -v gemini >/dev/null 2>&1; then
  say "gemini already present ($(gemini --version 2>&1 | head -1))"
else
  say "installing gemini CLI"
  npm install -g @google/gemini-cli >/dev/null 2>&1
  command -v gemini >/dev/null || { echo "gemini install failed" >&2; exit 1; }
  say "gemini installed ($(gemini --version 2>&1 | head -1))"
fi

# --- checkout ----------------------------------------------------------------------------------
mkdir -p "$WORK"
if [ ! -d "$WORK/.git" ]; then
  git init -q "$WORK"
  git -C "$WORK" remote add origin "$REPO_URL"
fi
# Fetch to FETCH_HEAD, never into refs/heads/review-target: git refuses to fetch into a branch that
# is checked out, so the direct form worked exactly once and every re-run died with rc=128. Found by
# running the script twice instead of once, which is the only way an idempotency claim is worth
# anything.
if ! git -C "$WORK" -c http.https://github.com/.extraheader="$AUTH" \
        fetch -q --depth 50 origin "$REF" +main:refs/remotes/origin/main 2>/tmp/review-host-fetch.err; then
  echo "could not fetch '$REF' from $REPO_URL" >&2
  sed 's/^/  /' /tmp/review-host-fetch.err >&2
  echo "  REF must be a BRANCH or TAG name. A bare commit SHA is refused by the server unless it" >&2
  echo "  allows reachable-SHA1-in-want; the branch head is the reviewed head in this loop anyway." >&2
  exit 1
fi
git -C "$WORK" checkout -q -B review-target FETCH_HEAD
say "checkout $WORK at $(git -C "$WORK" rev-parse --short HEAD) (ref $REF)"
say "base    origin/main at $(git -C "$WORK" rev-parse --short origin/main)"

# --- the environment a review needs ------------------------------------------------------------
ENVF="$WORK/.review-env"
{
  echo "export PATH=\"$NPM_CONFIG_PREFIX/bin:\$PATH\""
  echo "export GEMINI_API_KEY='$GEMINI_API_KEY'"
  echo "export GSTACK_PEER_REVIEW_DIR=\"$WORK/peer-reviews\""
  echo "export GSTACK_REVIEWER=gemini"
} > "$ENVF"
chmod 600 "$ENVF"

cat <<EOF

review host ready.

  source $ENVF
  cd $WORK
  python3 plugins/gstack-execution/scripts/peer_review.py open --builder claude --packet <packet.json>
  python3 plugins/gstack-execution/scripts/peer_review.py dispatch <review-id>
  python3 plugins/gstack-execution/scripts/peer_review.py collect  <review-id>

dispatch returns immediately and collect answers once. In THIS shell the dispatched
process survives between calls, which is the whole point; in device_bash it does not.
EOF
