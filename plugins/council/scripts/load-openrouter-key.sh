# shellcheck shell=bash
# Source this file (don't execute it) to populate OPENROUTER_API_KEY in the
# current shell. It delegates to the Python loader so the lookup logic stays
# in one place.
#
# Usage from a skill or workflow:
#     source "$(dirname "$0")/load-openrouter-key.sh"
#     curl -H "Authorization: Bearer $OPENROUTER_API_KEY" ...
#
# Or from anywhere, given the absolute path:
#     source "/path/to/plugins/council/scripts/load-openrouter-key.sh"
#
# The script is idempotent: if OPENROUTER_API_KEY is already set, it does nothing.
# On lookup failure it prints the loader's error to stderr and leaves the env
# unchanged — callers should check `[ -n "$OPENROUTER_API_KEY" ]` after sourcing.

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    # Use BASH_SOURCE if available (bash), else $0 (other shells sourcing this)
    _ork_self="${BASH_SOURCE[0]:-$0}"
    _ork_dir="$(cd "$(dirname "$_ork_self")" && pwd)"
    _ork_loader="$_ork_dir/openrouter_key.py"

    if [ ! -f "$_ork_loader" ]; then
        printf 'load-openrouter-key.sh: cannot find %s\n' "$_ork_loader" >&2
    else
        _ork_export_line="$(python3 "$_ork_loader" --export 2>/dev/null)"
        if [ -n "$_ork_export_line" ]; then
            # The loader emits a literal `export OPENROUTER_API_KEY='...'` line
            eval "$_ork_export_line"
        else
            # Re-run to surface the error message on stderr
            python3 "$_ork_loader" --export >/dev/null
        fi
        unset _ork_export_line
    fi

    unset _ork_self _ork_dir _ork_loader
fi
