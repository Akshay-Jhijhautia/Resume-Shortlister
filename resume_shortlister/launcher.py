"""Starting the app without a terminal, and the icon that does it.

``resume-shortlister open`` opens the running app in the browser, starting it in
the background first when it is not running. The icon the installers make with
``resume-shortlister launcher`` runs exactly that: an app in ``~/Applications``
(macOS, made on this computer, so it needs no signing), a Start menu and
desktop shortcut (Windows, with no console window) or an app menu entry
(Linux). ``resume-shortlister stop`` stops the app (the uninstallers run it
first, as Windows cannot remove a program that is running).

The running app is found from ``server.json`` in the data home, which the server
writes as it starts and removes as it stops. It counts only when its page
answers there, so a stale file never stops another program.
"""

from __future__ import annotations

import json
import os
import platform
import plistlib
import shutil
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import httpx

from . import __version__
from .config import data_home

APP_NAME = "Resume Shortlister"
SERVER_FILE = "server.json"
LOG_FILE = "app.log"
DEFAULT_PORT = 8765
START_SECONDS = 90  # the first start imports a lot; a slow disk takes a while
ASSETS = Path(__file__).parent / "assets"
# Marks the page as this app's (``web/app.py`` writes the token into it).
PAGE_MARK = 'name="resume-shortlister-token"'


# --- the running app ------------------------------------------------------------------------------------


def server_file(home: Path | None = None) -> Path:
    return (home or data_home()) / SERVER_FILE


def record_server(port: int, home: Path | None = None) -> Path:
    """Note that this process serves the app on ``port`` (``serve`` does, as it starts)."""
    path = server_file(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")
    return path


def _recorded(home: Path | None = None) -> dict | None:
    try:
        return json.loads(server_file(home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _answers(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200 and PAGE_MARK in response.text


def running(home: Path | None = None) -> str | None:
    """The address of the running app, when it answers."""
    recorded = _recorded(home)
    if not recorded:
        return None
    url = f"http://127.0.0.1:{recorded['port']}/"
    return url if _answers(url) else None


def free_port(preferred: int = DEFAULT_PORT) -> int:
    """``preferred`` when nothing listens there, else one the system picks."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return probe.getsockname()[1]
    raise OSError("No free port on 127.0.0.1.")


def python_command(windowless: bool = False) -> list[str]:
    """This installation's Python running the app's command line; on Windows ``windowless``
    picks ``pythonw``, which opens no console window."""
    python = Path(sys.executable)
    if windowless and os.name == "nt" and (python.parent / "pythonw.exe").exists():
        python = python.parent / "pythonw.exe"
    return [str(python), "-m", "resume_shortlister"]


def start(home: Path | None = None) -> str:
    """Start the app in the background, detached from this process; its address once it answers."""
    home = home or data_home()
    home.mkdir(parents=True, exist_ok=True)
    port = free_port()
    command = [*python_command(windowless=True), "web", "--no-browser", "--port", str(port)]
    # UTF-8 output whatever the locale: an app started from an icon may have none.
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "RESUME_SHORTLISTER_HOME": str(home)}
    options: dict = {"start_new_session": True}
    if os.name == "nt":
        options = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                   | subprocess.CREATE_NO_WINDOW}
    with open(home / LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} starting {APP_NAME} {__version__} on port {port}\n")
        log.flush()
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   env=env, **options)
    url = f"http://127.0.0.1:{port}/"
    deadline = time.monotonic() + START_SECONDS
    while time.monotonic() < deadline:
        if running(home) == url:  # answering, and recorded (what ``stop`` and the next ``open`` read)
            return url
        if process.poll() is not None:
            break
        time.sleep(0.3)
    raise RuntimeError(f"{APP_NAME} did not start. What it said:\n{_log_tail(home)}")


def _log_tail(home: Path, lines: int = 8) -> str:
    try:
        return "\n".join((home / LOG_FILE).read_text(encoding="utf-8").splitlines()[-lines:])
    except OSError:
        return "(no log)"


def open_app(browser: bool = True, home: Path | None = None) -> str:
    """Open the app in the browser (``browser`` False: only make sure it runs); its address."""
    url = running(home) or start(home)
    if browser:
        webbrowser.open(url)
    return url


def stop(home: Path | None = None, wait: float = 10.0) -> bool:
    """Stop the running app; False when none was running."""
    recorded = _recorded(home)
    if not recorded or not running(home):
        server_file(home).unlink(missing_ok=True)  # stale: its process is gone, or not this app
        return False
    os.kill(recorded["pid"], signal.SIGTERM)  # on Windows: ends the process
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline and running(home):
        time.sleep(0.2)
    server_file(home).unlink(missing_ok=True)
    return True


def tell(message: str) -> None:
    """Say ``message`` where it is seen: the terminal, or a dialog when started from an icon."""
    if sys.stderr is not None and sys.stderr.isatty():
        print(message, file=sys.stderr)
        return
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f"display alert {json.dumps(APP_NAME)} message {json.dumps(message)}"],
                           check=False, timeout=600)
        elif os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
        elif shutil.which("zenity"):
            subprocess.run(["zenity", "--error", f"--title={APP_NAME}", f"--text={message}"], check=False, timeout=600)
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", APP_NAME, message], check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass
    if sys.stderr is not None:
        print(message, file=sys.stderr)


# --- the icon -------------------------------------------------------------------------------------------


def launcher_paths(system: str | None = None, home: Path | None = None) -> list[Path]:
    """Where this system's launcher goes (Windows: the Start menu and the desktop)."""
    system = system or platform.system()
    home = home or Path.home()
    if system == "Darwin":
        return [home / "Applications" / f"{APP_NAME}.app"]
    if system == "Windows":
        programs = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        return [programs / f"{APP_NAME}.lnk", _windows_desktop(home) / f"{APP_NAME}.lnk"]
    data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return [data / "applications" / "resume-shortlister.desktop"]


def _windows_desktop(home: Path) -> Path:
    """The desktop folder (moved into OneDrive on many computers)."""
    try:
        found = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                               capture_output=True, text=True, timeout=30, check=True).stdout.strip()
        return Path(found) if found else home / "Desktop"
    except (OSError, subprocess.SubprocessError):
        return home / "Desktop"


def install_launcher(system: str | None = None, home: Path | None = None) -> list[Path]:
    """Make (or refresh) the icon that opens the app; the paths made."""
    system = system or platform.system()
    paths = launcher_paths(system, home)
    command = python_command(windowless=True) + ["open"]
    if system == "Darwin":
        _mac_app(paths[0], command)
    elif system == "Windows":
        for path in paths:
            _windows_shortcut(path, command)
    else:
        _desktop_entry(paths[0], command)
    return paths


def remove_launcher(system: str | None = None, home: Path | None = None) -> list[Path]:
    """Remove the icon; the paths that were there."""
    removed = []
    for path in launcher_paths(system, home):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            continue
        removed.append(path)
    return removed


def _mac_app(app: Path, command: list[str]) -> None:
    """A minimal app bundle whose program is a script running ``command``."""
    if app.exists():
        shutil.rmtree(app)
    program = app / "Contents" / "MacOS" / "resume-shortlister"
    program.parent.mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    program.write_text(
        "#!/bin/sh\n"
        f"# Made by {APP_NAME}'s installer: opens the app, starting it first when it is not running.\n"
        f"exec {' '.join(_sh_quote(part) for part in command)}\n",
        encoding="utf-8",
    )
    program.chmod(0o755)
    shutil.copyfile(ASSETS / "icon.icns", app / "Contents" / "Resources" / "icon.icns")
    with open(app / "Contents" / "Info.plist", "wb") as plist:
        plistlib.dump({
            "CFBundleName": APP_NAME, "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": "io.github.akshay-jhijhautia.resume-shortlister",
            "CFBundleExecutable": program.name, "CFBundleIconFile": "icon.icns",
            "CFBundlePackageType": "APPL", "CFBundleShortVersionString": __version__,
            "LSMinimumSystemVersion": "11.0", "NSHighResolutionCapable": True,
        }, plist)


def _sh_quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def _desktop_entry(path: Path, command: list[str]) -> None:
    """A freedesktop.org entry, shown in the app menu of GNOME, KDE and the others."""
    path.parent.mkdir(parents=True, exist_ok=True)
    exec_line = " ".join(f'"{part}"' if " " in part else part for part in command)
    path.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Explainable resume screening, on this computer\n"
        f"Exec={exec_line}\n"
        f"Icon={ASSETS / 'icon.png'}\n"
        "Terminal=false\n"
        "Categories=Office;\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _windows_shortcut(path: Path, command: list[str]) -> None:
    """A shortcut made with Windows' own scripting object (no extra package needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["powershell", "-NoProfile", "-Command", shortcut_script(path, command)],
                   check=True, capture_output=True, timeout=60)


def shortcut_script(path: Path, command: list[str]) -> str:
    """The PowerShell that makes the shortcut at ``path`` running ``command``."""
    def quoted(text: str) -> str:
        return "'" + text.replace("'", "''") + "'"
    arguments = " ".join(f'"{part}"' if " " in part else part for part in command[1:])
    return (
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut({quoted(str(path))}); "
        f"$s.TargetPath = {quoted(command[0])}; $s.Arguments = {quoted(arguments)}; "
        f"$s.IconLocation = {quoted(str(ASSETS / 'icon.ico'))}; $s.Description = {quoted(f'Open {APP_NAME}')}; "
        f"$s.WorkingDirectory = {quoted(str(Path.home()))}; $s.Save()"
    )
