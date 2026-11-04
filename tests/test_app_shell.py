"""The web app for people who never open a terminal: setting up the chat model in the page,
quitting, the update notice, and progress while resumes are read."""

import dataclasses
import json
import os
import stat
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from resume_shortlister import __version__, config, updates
from resume_shortlister.config import get_settings, save_env
from resume_shortlister.rag import resume_rag
from resume_shortlister.services import Services
from resume_shortlister.web.app import TOKEN_HEADER, create_app
from tests.paths import RESUMES_DIR
from tests.test_web import TOKEN, _new, _said, events

KEY_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY",
            "LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL")


@pytest.fixture
def fresh(monkeypatch, tmp_path):
    """A first start: no key anywhere, the app reading its settings as ``serve`` does. The
    working directory has no ``.env`` (a developer's own key is never read)."""
    for name in KEY_VARS:  # recorded, so what the setup page sets is undone after the test
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    config.get_settings.cache_clear()
    app = create_app(lambda: Services.from_settings(dataclasses.replace(get_settings(), embedder="hashing")),
                     token=TOKEN)
    return TestClient(app, base_url="http://127.0.0.1", headers={TOKEN_HEADER: TOKEN})


def _env_file() -> str:
    return os.path.join(os.environ["RESUME_SHORTLISTER_HOME"], ".env")


# --- saving settings ------------------------------------------------------------------------------------


def test_saving_settings_keeps_the_other_lines_and_only_the_owner_reads_them(tmp_path):
    path = tmp_path / "home" / ".env"
    path.parent.mkdir()
    path.write_text("﻿# mine\nSHORTLIST_SIZE=15\nexport LLM_MODEL=gpt-old\nOPENAI_API_KEY=old", encoding="utf-8")
    save_env(path, {"OPENAI_API_KEY": "sk-new", "LLM_MODEL": None, "LLM_PROVIDER": "openai"})
    assert path.read_text(encoding="utf-8") == "# mine\nSHORTLIST_SIZE=15\nOPENAI_API_KEY=sk-new\nLLM_PROVIDER=openai\n"
    if sys.platform != "win32":  # Windows keeps a user's files private through their folder
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in path.parent.iterdir()] == [".env"]  # no temporary file left


# --- setup in the page ----------------------------------------------------------------------------------


def test_a_first_start_asks_for_a_key_then_is_ready_without_a_restart(fresh):
    status = fresh.get("/api/status").json()
    assert status["needs_setup"] is True and status["ready"] is False

    options = fresh.get("/api/setup").json()
    assert options["current"] == "openai"
    openai = next(p for p in options["providers"] if p["name"] == "openai")
    assert openai["key_var"] == "OPENAI_API_KEY" and openai["key_set"] is False and openai["installed"]
    assert openai["help_url"].startswith("https://")

    status = fresh.post("/api/setup", json={"provider": "openai", "api_key": " sk-proj-abc_123-XYZ "}).json()
    assert status["needs_setup"] is False and status["ready"] is True
    with open(_env_file(), encoding="utf-8") as saved:
        assert "OPENAI_API_KEY=sk-proj-abc_123-XYZ\n" in saved.read()
    # No answer ever contains the key.
    for path in ("/api/status", "/api/settings", "/api/setup"):
        assert "sk-proj-abc_123-XYZ" not in fresh.get(path).text


def test_switching_provider_drops_the_other_providers_model(fresh, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gpt-old")
    status = fresh.post("/api/setup", json={"provider": "anthropic", "api_key": "sk-ant-api03-abcdefgh"}).json()
    assert status["model"] == "Anthropic claude-opus-5-5" and status["ready"] is True
    assert "LLM_MODEL" not in os.environ
    # Back to OpenAI: its key was never given, so it is asked for.
    response = fresh.post("/api/setup", json={"provider": "openai"})
    assert response.status_code == 422 and "Paste your OpenAI API key" in response.json()["detail"]


def test_ollama_needs_a_model_and_no_key(fresh):
    response = fresh.post("/api/setup", json={"provider": "ollama"})
    assert response.status_code == 422 and "model" in response.json()["detail"]
    status = fresh.post("/api/setup", json={"provider": "ollama", "model": "qwen3:32b"}).json()
    assert status["model"] == "Ollama qwen3:32b" and status["ready"] is True


@pytest.mark.parametrize("key", ["sk-abc def", "sk-abc\nLLM_BASE_URL=http://evil", "short", "sk-'quoted'"])
def test_a_key_that_could_change_other_settings_is_refused(fresh, key):
    response = fresh.post("/api/setup", json={"provider": "openai", "api_key": key})
    assert response.status_code == 422
    assert not os.path.exists(_env_file())


def test_setup_waits_for_a_running_screening(fresh):
    session = fresh.app.state.workspace.get(_new(fresh))
    with session.busy:
        response = fresh.post("/api/setup", json={"provider": "openai", "api_key": "sk-proj-abcdefgh"})
    assert response.status_code == 409


def test_open_sessions_go_on_with_the_new_model(fresh):
    new = _new(fresh)  # opened by the page before setup: nothing said, so not saved yet
    fresh.post("/api/setup", json={"provider": "openai", "api_key": "sk-proj-abcdefgh"})
    said = _new(fresh)
    events(fresh.post(f"/api/sessions/{said}/folder", json={"path": str(RESUMES_DIR)}))  # saved now
    fresh.post("/api/setup", json={"provider": "anthropic", "api_key": "sk-ant-api03-abcdefgh"})
    for session_id in (new, said):
        session = fresh.app.state.workspace.get(session_id)
        assert session.services.settings.llm_provider == "anthropic"
    assert fresh.app.state.workspace.get(said).services.pool is not None  # its resumes reloaded


# --- quitting -------------------------------------------------------------------------------------------


def test_quit_stops_the_server_once_it_has_answered(fresh, monkeypatch):
    assert fresh.post("/api/quit").status_code == 409  # not started by ``serve``
    stopped = []
    fresh.app.state.quit = lambda: stopped.append(True)
    started = []
    monkeypatch.setattr("resume_shortlister.web.app.threading.Timer",
                        lambda delay, action: type("T", (), {"start": lambda self: started.append(action)})())
    assert fresh.post("/api/quit").status_code == 204
    assert stopped == [] and len(started) == 1  # stopped after the answer, not before
    started[0]()
    assert stopped == [True]
    assert fresh.post("/api/quit", headers={TOKEN_HEADER: "wrong"}).status_code == 403  # only this page may


# --- updates --------------------------------------------------------------------------------------------


def test_pypi_is_asked_at_most_once_a_day(tmp_path):
    cache, asked = tmp_path / "update-check.json", []

    def fetch():
        asked.append(True)
        return "9.0.0"

    now = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
    assert updates.latest_version(cache, now, fetch) == "9.0.0"
    assert updates.latest_version(cache, now + timedelta(hours=23), fetch) == "9.0.0"
    assert len(asked) == 1
    assert updates.latest_version(cache, now + timedelta(hours=25), fetch) == "9.0.0" and len(asked) == 2


def test_an_unreachable_pypi_gives_the_last_answer_and_waits_a_day(tmp_path):
    cache = tmp_path / "update-check.json"
    now = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
    assert updates.latest_version(cache, now) is None  # offline (conftest), nothing known
    cache.write_text(json.dumps({"checked": (now - timedelta(days=2)).isoformat(), "latest": "1.9.0"}), encoding="utf-8")
    assert updates.latest_version(cache, now) == "1.9.0"
    assert json.loads(cache.read_text(encoding="utf-8"))["checked"] == now.isoformat()  # not asked again today


@pytest.mark.parametrize("latest, newer", [("9.0.0", True), ("1.3.1", True), ("1.10.0", True), ("1.3.0", False),
                                           ("1.2.9", False), ("10.0.0rc1", False), (None, False)])
def test_only_a_later_release_is_offered(latest, newer):
    assert updates.is_newer(latest, "1.3.0") is newer
    assert not updates.is_newer(__version__, __version__)


def test_the_update_notice(fresh, monkeypatch):
    monkeypatch.setattr(updates, "_fetch", lambda: "99.0.0")
    view = fresh.get("/api/update").json()
    assert view == {"current": __version__, "latest": "99.0.0", "available": True, "checks": True,
                    "how": updates.install_command()}
    assert updates.install_command(windows=True).startswith("powershell -ExecutionPolicy ByPass")
    assert updates.install_command(windows=False).startswith("curl -LsSf")


def test_the_update_check_can_be_turned_off(fresh, monkeypatch):
    monkeypatch.setenv("RESUME_SHORTLISTER_UPDATE_CHECK", "false")
    monkeypatch.setattr(updates, "_fetch", lambda: pytest.fail("asked PyPI although turned off"))
    config.get_settings.cache_clear()
    assert fresh.get("/api/update").json()["checks"] is False
    assert fresh.get("/api/settings").json()["update_check"] is False


# --- progress -------------------------------------------------------------------------------------------


class _LocalLike(resume_rag.HashingEmbedder):
    """The hashing embedder, loaded like a local model (``prepare``)."""

    prepared = 0

    def prepare(self, progress=None):
        if progress:
            progress("Getting the language model ready (a 1 MB download the first time)…")
        _LocalLike.prepared += 1


def test_indexing_says_how_far_it_is_and_readies_the_model_first(tmp_path):
    folder = tmp_path / "applicants"
    folder.mkdir()
    for name in ("resume_john_doe.pdf", "resume_alex_lee.txt"):
        (folder / name).write_bytes((RESUMES_DIR / name).read_bytes())
    rag = resume_rag.ResumeRAG(str(tmp_path / "index"), embedder=_LocalLike())
    said = []
    rag.index_directory(str(folder), progress=said.append)
    assert said == ["Getting the language model ready (a 1 MB download the first time)…",
                    "Reading resumes: 1 of 2", "Reading resumes: 2 of 2"]
    said.clear()
    rag.index_directory(str(folder), progress=said.append)
    assert said == [] and _LocalLike.prepared == 1  # nothing new: no progress, no model


def test_a_loaded_folder_streams_its_progress(fresh, tmp_path):
    folder = tmp_path / "applicants"
    folder.mkdir()
    (folder / "resume_alex_lee.txt").write_bytes((RESUMES_DIR / "resume_alex_lee.txt").read_bytes())
    fresh.post("/api/setup", json={"provider": "openai", "api_key": "sk-proj-abcdefgh"})
    streamed = events(fresh.post(f"/api/sessions/{_new(fresh)}/folder", json={"path": str(folder)}))
    assert _said(streamed, "progress") == ["Reading resumes: 1 of 1"]
    assert "1 ready" in _said(streamed)[0]
