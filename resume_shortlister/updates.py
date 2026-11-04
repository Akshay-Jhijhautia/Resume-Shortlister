"""Whether a newer version is out, for the web app's update notice.

The newest version number is read from PyPI's public page for the package, at
most once a day, and remembered in the data home. The request says nothing
about the user or their resumes (PyPI sees what any web request shows: that a
computer asked). It never stops the app: when it fails, there is no notice.
``RESUME_SHORTLISTER_UPDATE_CHECK=false`` turns it off.

Updating is running the one-line install again, which keeps the key and data.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

PYPI_URL = "https://pypi.org/pypi/resume-shortlister/json"
CHECK_EVERY = timedelta(days=1)
TIMEOUT_SECONDS = 3.0
_RAW = "https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main"
# The one-line installs (as in the README); run again, they update.
INSTALL_COMMANDS = {
    "windows": f'powershell -ExecutionPolicy ByPass -c "irm {_RAW}/install.ps1 | iex"',
    "unix": f"curl -LsSf {_RAW}/install.sh | sh",
}


def install_command(windows: bool | None = None) -> str:
    """The install line for this computer (``windows`` forces one)."""
    return INSTALL_COMMANDS["windows" if (os.name == "nt" if windows is None else windows) else "unix"]


def _fetch() -> str:
    response = httpx.get(PYPI_URL, timeout=TIMEOUT_SECONDS, follow_redirects=True)
    response.raise_for_status()
    return response.json()["info"]["version"]


def latest_version(cache_file: Path, now: datetime | None = None, fetch: Callable[[], str] | None = None) -> str | None:
    """The newest version on PyPI, asked at most once per ``CHECK_EVERY`` (remembered in
    ``cache_file``); the last answer, or None, when PyPI cannot be reached."""
    now, fetch = now or datetime.now(timezone.utc), fetch or _fetch
    try:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if now - datetime.fromisoformat(cached["checked"]) < CHECK_EVERY:
            return cached.get("latest")
    except (OSError, ValueError, KeyError, TypeError):
        cached = {}
    try:
        latest = fetch()
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        latest = cached.get("latest")  # tried today: ask again tomorrow, not on every page load
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"checked": now.isoformat(), "latest": latest}), encoding="utf-8")
    except OSError:
        pass
    return latest


def is_newer(latest: str | None, current: str) -> bool:
    """Whether ``latest`` is a later release than ``current`` (plain "1.4.0" versions; anything
    else, such as a pre-release, is never offered)."""
    try:
        return latest is not None and _parts(latest) > _parts(current)
    except ValueError:
        return False


def _parts(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))
