#!/bin/sh
# Remove Resume Shortlister from macOS or Linux:
#
#   curl -LsSf https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main/uninstall.sh | sh
#
# It stops the app, removes its icon and the resume-shortlister command, and asks before
# deleting your data (screenings, indexes, uploaded copies, your key, the language model).
# uv, which the installer brought, stays: other programs may use it.

set -eu

say() { printf '%s\n' "$*"; }

bin="${XDG_BIN_HOME:-$HOME/.local/bin}"
command="$(command -v resume-shortlister 2>/dev/null || printf '%s' "$bin/resume-shortlister")"
uv="$(command -v uv 2>/dev/null || printf '%s' "$bin/uv")"

# 1. The app and its icon
if [ -x "$command" ]; then
    "$command" stop || true
    "$command" launcher --remove || true
fi

# 2. The command
if [ -x "$uv" ] && "$uv" tool list 2>/dev/null | grep -q '^resume-shortlister '; then
    "$uv" tool uninstall resume-shortlister
    say "Removed the resume-shortlister command."
else
    say "The resume-shortlister command was not installed with uv; if you installed it with pip, run: pip uninstall resume-shortlister"
fi

# 3. Your data, only when you say so, and only the app's own folder
home="${RESUME_SHORTLISTER_HOME:-${PROFILE_MATCH_HOME:-}}"
if [ -z "$home" ]; then
    home="$HOME/.resume-shortlister"
    [ -d "$HOME/.profile-match" ] && [ ! -e "$home" ] && home="$HOME/.profile-match"
fi
if [ -d "$home" ]; then
    case "$(basename "$home")" in
        .resume-shortlister | .profile-match) ours=1 ;;
        *) ours=0 ;;
    esac
    answer=""
    if [ "$ours" = 1 ] && (: </dev/tty) 2>/dev/null; then
        printf 'Also delete your data in %s (screenings, indexes, uploaded copies, your key, the language model)? [y/N] ' "$home" >/dev/tty
        IFS= read -r answer </dev/tty || answer=""
    fi
    case "$answer" in
        y | Y | yes | YES | Yes)
            rm -rf "$home"
            say "Deleted $home."
            ;;
        *) say "Kept your data in $home; delete that folder to remove it." ;;
    esac
fi

say "Done. uv stays installed; to remove it too, see https://docs.astral.sh/uv/getting-started/installation/#uninstallation"
