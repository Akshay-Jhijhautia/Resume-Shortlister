#!/bin/sh
# Install Resume Shortlister on macOS or Linux, with nothing installed beforehand:
#
#   curl -LsSf https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main/install.sh | sh
#   wget -qO- https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main/install.sh | sh
#
# It installs uv (a small Python installer, into ~/.local/bin) unless you have it, lets uv
# fetch its own Python, installs Resume Shortlister as the `resume-shortlister` command,
# asks once for your OpenAI API key, and puts Resume Shortlister in Applications (macOS) or
# the app menu (Linux). No sudo, git or Python needed. Running it again upgrades to the
# newest version and keeps your key and data. To remove it: uninstall.sh, next to this file.
#
# Settings (environment variables), for testing or another source:
#   RESUME_SHORTLISTER_PACKAGE   what to install (default: from PyPI, with every chat provider)
#   RESUME_SHORTLISTER_PYTHON    the Python version uv uses (default: 3.12)
#   RESUME_SHORTLISTER_HOME      the data folder, where the key is kept (default: ~/.resume-shortlister)

set -eu

package="${RESUME_SHORTLISTER_PACKAGE:-resume-shortlister[anthropic,google,ollama]}"
python="${RESUME_SHORTLISTER_PYTHON:-3.12}"

say() { printf '%s\n' "$*"; }
fail() { say "Error: $*" >&2; exit 1; }

case "$(uname -s)" in
    Darwin | Linux) ;;
    *) fail "this installer is for macOS and Linux; Windows support is planned." ;;
esac

# 1. uv
if command -v uv >/dev/null 2>&1; then
    uv=uv
else
    say "Installing uv (the installer for Python apps)..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | UV_PRINT_QUIET=1 sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | UV_PRINT_QUIET=1 sh
    else
        fail "neither curl nor wget is installed; install one and run this again."
    fi
    uv="${XDG_BIN_HOME:-$HOME/.local/bin}/uv"
    [ -x "$uv" ] || fail "uv did not install; see https://docs.astral.sh/uv/ and run this again."
fi

# 2. Resume Shortlister, with its own Python (downloaded by uv when this computer lacks it)
say "Installing Resume Shortlister (a minute or two the first time)..."
PATH="$("$uv" tool dir --bin):$PATH"
"$uv" tool install --upgrade --python "$python" "$package"
"$uv" tool update-shell >/dev/null 2>&1 || true
command="$("$uv" tool dir --bin)/resume-shortlister"
[ -x "$command" ] || fail "the resume-shortlister command was not installed."
say "Installed: $("$command" --version)"

# 3. The API key, kept in the data folder the app reads (asked only when none is there)
home="${RESUME_SHORTLISTER_HOME:-${PROFILE_MATCH_HOME:-}}"
if [ -z "$home" ]; then
    home="$HOME/.resume-shortlister"
    [ -d "$HOME/.profile-match" ] && [ ! -e "$home" ] && home="$HOME/.profile-match"
fi
env_file="$home/.env"

if [ -f "$env_file" ] && grep -Eq '^[[:space:]]*(OPENAI|ANTHROPIC|GOOGLE|LLM)_API_KEY=.' "$env_file"; then
    say "Your API key is already set in $env_file."
elif (: </dev/tty) 2>/dev/null; then
    # Read from the terminal: when piped from curl, this script's own input is the script.
    # Typing is hidden before the prompt appears, and shown again however this ends (Ctrl-C too).
    trap 'stty echo </dev/tty 2>/dev/null || true' EXIT
    trap 'exit 130' INT TERM
    stty -echo </dev/tty 2>/dev/null || true
    printf 'Paste your OpenAI API key (hidden), or press Enter to skip: ' >/dev/tty
    IFS= read -r key </dev/tty || key=""
    stty echo </dev/tty 2>/dev/null || true
    trap - EXIT INT TERM
    printf '\n' >/dev/tty
    if [ -n "$key" ]; then
        mkdir -p "$home"
        if [ -s "$env_file" ] && [ -n "$(tail -c 1 "$env_file")" ]; then
            printf '\n' >>"$env_file"
        fi
        (umask 077 && printf 'OPENAI_API_KEY=%s\n' "$key" >>"$env_file")
        chmod 600 "$env_file"
        say "Saved your key in $env_file (only you can read it)."
    else
        say "Skipped: the app asks for your key when it first starts, and lets you choose another provider."
    fi
else
    say "The app asks for your API key when it first starts."
fi

# 4. The icon that opens the app: in Applications (macOS) or the app menu (Linux)
if "$command" launcher >/dev/null 2>&1; then
    case "$(uname -s)" in
        Darwin) where="Applications (or Spotlight: type Resume Shortlister)" ;;
        *) where="your app menu" ;;
    esac
else
    where=""
fi

say ""
if [ -n "$where" ]; then
    say "Done. Open Resume Shortlister from $where."
else
    say "Done."
fi
say "Or, in a new terminal window: resume-shortlister open"
say ""

# Started now for the person at this computer (a terminal, and a screen to show it on).
if (: </dev/tty) 2>/dev/null && { [ "$(uname -s)" = Darwin ] || [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; }; then
    say "Starting it now..."
    "$command" open >/dev/null || true
fi
