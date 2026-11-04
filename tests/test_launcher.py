"""Starting the app without a terminal: the icon on each system, and open / stop."""

import json
import os
import plistlib
import stat
import sys
from pathlib import Path

import pytest

from resume_shortlister import __version__, launcher
from resume_shortlister.app import main


# --- the icon -------------------------------------------------------------------------------------------


def test_the_mac_app_is_made_here_and_runs_this_installation(tmp_path):
    [app] = launcher.install_launcher("Darwin", home=tmp_path)
    assert app == tmp_path / "Applications" / "Resume Shortlister.app"
    with open(app / "Contents" / "Info.plist", "rb") as plist:
        info = plistlib.load(plist)
    assert info["CFBundleName"] == "Resume Shortlister" and info["CFBundleShortVersionString"] == __version__
    program = app / "Contents" / "MacOS" / info["CFBundleExecutable"]
    assert program.read_text(encoding="utf-8").splitlines()[-1] == (
        f"exec '{sys.executable}' '-m' 'resume_shortlister' 'open'")
    if os.name != "nt":
        assert program.stat().st_mode & stat.S_IXUSR
    assert (app / "Contents" / "Resources" / info["CFBundleIconFile"]).read_bytes()[:4] == b"icns"

    launcher.install_launcher("Darwin", home=tmp_path)  # made again over the old one: an update
    assert launcher.remove_launcher("Darwin", home=tmp_path) == [app] and not app.exists()
    assert launcher.remove_launcher("Darwin", home=tmp_path) == []


def test_the_linux_entry_is_in_the_app_menu(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    [entry] = launcher.install_launcher("Linux", home=tmp_path)
    assert entry == tmp_path / ".local" / "share" / "applications" / "resume-shortlister.desktop"
    lines = dict(line.split("=", 1) for line in entry.read_text(encoding="utf-8").splitlines()[1:])
    assert lines["Name"] == "Resume Shortlister" and lines["Terminal"] == "false"
    assert lines["Exec"].endswith("-m resume_shortlister open")
    assert Path(lines["Icon"]).read_bytes()[:4] == b"\x89PNG"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert launcher.launcher_paths("Linux", home=tmp_path) == [tmp_path / "data" / "applications" / "resume-shortlister.desktop"]


def test_the_windows_shortcuts_run_python_without_a_console(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setattr(launcher, "_windows_desktop", lambda home: tmp_path / "OneDrive" / "Desktop")
    start_menu, desktop = launcher.launcher_paths("Windows", home=tmp_path)
    assert start_menu == tmp_path / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Resume Shortlister.lnk"
    assert desktop == tmp_path / "OneDrive" / "Desktop" / "Resume Shortlister.lnk"

    script = launcher.shortcut_script(Path(r"C:\Users\O'Brien\Desktop\Resume Shortlister.lnk"),
                                      [r"C:\Users\O'Brien\.local\share\uv\tools\resume-shortlister\Scripts\pythonw.exe",
                                       "-m", "resume_shortlister", "open"])
    assert r"CreateShortcut('C:\Users\O''Brien\Desktop\Resume Shortlister.lnk')" in script  # quotes doubled
    assert r"TargetPath = 'C:\Users\O''Brien\.local\share\uv\tools\resume-shortlister\Scripts\pythonw.exe'" in script
    assert "Arguments = '-m resume_shortlister open'" in script
    assert "icon.ico'" in script


def test_the_icons_are_in_the_package():
    assert {path.name for path in launcher.ASSETS.iterdir()} >= {"icon.png", "icon.icns", "icon.ico"}


# --- open and stop --------------------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path):
    home = tmp_path / "data"
    yield home
    launcher.stop(home)  # never leave a server behind


def test_open_starts_the_app_once_and_stop_stops_it(home):
    url = launcher.open_app(browser=False, home=home)
    assert url.startswith("http://127.0.0.1:") and launcher.running(home) == url
    recorded = json.loads(launcher.server_file(home).read_text(encoding="utf-8"))
    assert recorded["pid"] != os.getpid()  # a process of its own, outliving this one
    assert launcher.open_app(browser=False, home=home) == url  # running already: not started again

    assert launcher.stop(home) is True
    assert launcher.running(home) is None and not launcher.server_file(home).exists()
    assert launcher.stop(home) is False


def test_a_stale_record_stops_nothing(home):
    home.mkdir()
    port = launcher.free_port(1)  # nothing listens there
    launcher.server_file(home).write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")
    assert launcher.running(home) is None
    assert launcher.stop(home) is False  # this test process (the recorded pid) is still alive
    assert not launcher.server_file(home).exists()


def test_a_start_that_fails_says_why(home, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nonsense")
    with pytest.raises(RuntimeError, match="Unknown LLM_PROVIDER 'nonsense'"):
        launcher.start(home)


def test_the_commands(home, monkeypatch, capsys):
    monkeypatch.setenv("RESUME_SHORTLISTER_HOME", str(home))
    assert main(["open", "--no-browser"]) == 0
    url = capsys.readouterr().out.strip()
    assert launcher.running(home) == url
    assert main(["stop"]) == 0 and "Stopped Resume Shortlister." in capsys.readouterr().out
    assert main(["stop"]) == 0 and "was not running" in capsys.readouterr().out
