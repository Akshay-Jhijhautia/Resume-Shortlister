"""Runtime settings, read once from the environment and ``.env`` files.

Local data (folder indexes, uploaded resumes, saved sessions) lives under one
data home, ``~/.resume-shortlister`` unless ``RESUME_SHORTLISTER_HOME`` says otherwise,
so the tool works the same from any directory. ``.env`` is read from the
current directory and from the data home, in that order of precedence.

The chat model comes from ``LLM_PROVIDER`` and ``LLM_MODEL`` (see
``providers``). The older ``OPENAI_MODEL``, ``OPENAI_TEMPERATURE``,
``OPENAI_TIMEOUT`` and ``OPENAI_MAX_RETRIES`` still configure the OpenAI
provider when the ``LLM_`` names are unset, and ``CHROMA_DB_DIR`` still sets
the index folder (now ``INDEX_DIR``).

Before 1.2 the tool was called Profile Match: its ``PROFILE_MATCH_*`` settings
and its data home ``~/.profile-match`` still work (see ``tool_env`` and
``default_home``). The data home is used where it is, never moved: saved
sessions and indexes record paths inside it.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from . import providers

def default_home(user_home: Path | None = None) -> Path:
    """``~/.resume-shortlister``, or the data home from before the rename
    (``~/.profile-match``) when only that one exists."""
    user_home = user_home or Path.home()
    current, legacy = user_home / ".resume-shortlister", user_home / ".profile-match"
    return legacy if legacy.is_dir() and not current.exists() else current


DEFAULT_HOME = default_home()


def _env(*names: str | None) -> str | None:
    """The first of ``names`` set to a non-empty value."""
    return next((os.environ[name] for name in names if name and os.getenv(name)), None)


def tool_env(name: str) -> str | None:
    """The ``RESUME_SHORTLISTER_<name>`` setting, or its name from before the rename
    (``PROFILE_MATCH_<name>``)."""
    return _env(f"RESUME_SHORTLISTER_{name}", f"PROFILE_MATCH_{name}")


def _optional_float(*names: str | None) -> float | None:
    value = _env(*names)
    return float(value) if value is not None else None


def _yes(value: str | None, default: bool | None) -> bool | None:
    return default if value in (None, "") else value.strip().lower() in {"1", "true", "yes", "on"}


def _flag(name: str, default: bool | None) -> bool | None:
    return _yes(os.getenv(name), default)


# Where each local data path is inside the data home, unless set on its own.
HOME_PATHS = {
    "db_dir": "index", "uploads_dir": "uploads", "sessions_db": "sessions.sqlite",
    "models_dir": "models", "llm_cache_db": "llm_cache.sqlite",
}


@dataclass(frozen=True)
class Settings:
    # openai, anthropic, google or ollama (see ``providers.PROVIDERS``).
    llm_provider: str = "openai"
    # Empty: the provider's default model.
    llm_model: str = ""
    # None keeps the provider default; newer models accept no other value.
    llm_temperature: float | None = None
    llm_timeout: float = 60.0
    llm_max_retries: int = 2
    # An OpenAI-compatible server for the openai provider, or the Ollama server.
    llm_base_url: str | None = None
    # OpenAI's Responses API, needed for tool calling with reasoning models (gpt-5.6, gpt-6).
    # None: on for OpenAI itself, off for OpenAI-compatible servers, which rarely have it.
    llm_responses_api: bool | None = None
    # Local data: one folder holding the indexes, uploads and sessions below. Each path left
    # empty is that file or folder inside ``home`` (``HOME_PATHS``), so a different home never
    # mixes its data with the default one.
    home: str = str(DEFAULT_HOME)
    db_dir: str = ""
    # Where resumes uploaded in chat (or given as files) are copied, one subfolder per batch.
    uploads_dir: str = ""
    # Saved chat sessions (SQLite).
    sessions_db: str = ""
    # Resume embeddings: "local" (an open-source model on this machine, the default),
    # "openai", or "hashing" (offline, keyword overlap only; for tests).
    embedder: str = "local"
    # Where the local embedding model is downloaded (once).
    models_dir: str = ""
    # The only directory the agent may write to (reports, summaries).
    reports_dir: str = "reports"
    # Candidates kept after the initial screen.
    shortlist_size: int = 10
    # 1: retrieval only; 2: + deep analysis of the shortlist; 3: + interview recommendations.
    screening_rounds: int = 3
    # Save the shortlist and per-candidate reports under reports_dir after every screening.
    save_reports: bool = True
    # Reuse the model's answer to a question asked before (see ``llm_cache``).
    llm_cache: bool = True
    llm_cache_db: str = ""
    # Ask PyPI once a day whether a newer version is out (see ``updates``).
    update_check: bool = True

    @classmethod
    def from_env(cls) -> Settings:
        defaults = cls()
        home = Path(tool_env("HOME") or defaults.home).expanduser()
        provider = (os.getenv("LLM_PROVIDER") or defaults.llm_provider).strip().lower()
        # The older OPENAI_ names configure only the OpenAI provider.
        legacy = "OPENAI_{}".format if provider == "openai" else lambda _: None
        return cls(
            llm_provider=provider,
            llm_model=_env("LLM_MODEL", legacy("MODEL")) or "",  # "": the provider default
            llm_temperature=_optional_float("LLM_TEMPERATURE", legacy("TEMPERATURE")),
            llm_timeout=_optional_float("LLM_TIMEOUT", legacy("TIMEOUT")) or defaults.llm_timeout,
            llm_max_retries=int(_env("LLM_MAX_RETRIES", legacy("MAX_RETRIES")) or defaults.llm_max_retries),
            llm_base_url=_env("LLM_BASE_URL"),
            llm_responses_api=_flag("OPENAI_RESPONSES_API", defaults.llm_responses_api),
            home=str(home),
            db_dir=_env("INDEX_DIR", "CHROMA_DB_DIR") or "",
            uploads_dir=os.getenv("UPLOADS_DIR") or "",
            sessions_db=os.getenv("SESSIONS_DB") or "",
            embedder=os.getenv("EMBEDDER") or defaults.embedder,
            models_dir=os.getenv("MODELS_DIR") or "",
            reports_dir=os.getenv("REPORTS_DIR") or defaults.reports_dir,
            shortlist_size=int(os.getenv("SHORTLIST_SIZE") or defaults.shortlist_size),
            screening_rounds=int(os.getenv("SCREENING_ROUNDS") or defaults.screening_rounds),
            save_reports=_flag("SAVE_REPORTS", defaults.save_reports),
            llm_cache=_flag("LLM_CACHE", defaults.llm_cache),
            llm_cache_db=os.getenv("LLM_CACHE_DB") or "",
            update_check=_yes(tool_env("UPDATE_CHECK"), defaults.update_check),
        )

    def __post_init__(self) -> None:
        home = Path(self.home).expanduser()
        for name, inside in HOME_PATHS.items():
            if not getattr(self, name):
                object.__setattr__(self, name, str(home / inside))
        provider = providers.get(self.llm_provider)
        if not self.llm_model:
            if provider.default_model is None:
                raise ValueError(f"Set LLM_MODEL to the {provider.label} model to use (for example from: ollama list).")
            object.__setattr__(self, "llm_model", provider.default_model)
        if self.llm_temperature is not None and not provider.takes_temperature:
            raise ValueError(f"{provider.label} models accept no temperature; unset LLM_TEMPERATURE.")
        if not 1 <= self.screening_rounds <= 3:
            raise ValueError(f"screening_rounds must be 1, 2 or 3, got {self.screening_rounds}")
        if self.shortlist_size < 1:
            raise ValueError(f"shortlist_size must be at least 1, got {self.shortlist_size}")
        if self.embedder not in {"local", "openai", "hashing"}:
            raise ValueError(f"embedder must be local, openai or hashing, got {self.embedder}")

    @property
    def responses_api(self) -> bool:
        return self.llm_responses_api if self.llm_responses_api is not None else not self.llm_base_url

    @property
    def model_label(self) -> str:
        """The chat model as people read it, e.g. "Anthropic claude-opus-5-5"."""
        return f"{providers.get(self.llm_provider).label} {self.llm_model}"


# A ``.env`` line setting a variable: ``NAME=value`` or ``export NAME=value``.
_ENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def env_file(settings: Settings) -> Path:
    """The data home's ``.env``, where settings made in the app are saved."""
    return Path(settings.home).expanduser() / ".env"


def save_env(path: Path, values: dict[str, str | None]) -> None:
    """Set each of ``values`` in the ``.env`` file at ``path`` (``None`` removes it), keeping
    its other lines. The file is readable by its owner only, and replaced in one step, so
    it is never left half written."""
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    kept = [line for line in lines if not ((m := _ENV_LINE_RE.match(line)) and m.group(1) in values)]
    kept += [f"{name}={value}" for name, value in values.items() if value is not None]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".env-{uuid.uuid4().hex}.tmp")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w",
                   encoding="utf-8", newline="\n") as out:
        out.write("".join(f"{line}\n" for line in kept))
    os.replace(temporary, path)


def load_env_files() -> None:
    """Load ``.env`` from the current directory, then from the data home (no overrides)."""
    load_dotenv(find_dotenv(usecwd=True))
    home = Path(tool_env("HOME") or DEFAULT_HOME).expanduser()
    load_dotenv(home / ".env")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_env_files()
    return Settings.from_env()
