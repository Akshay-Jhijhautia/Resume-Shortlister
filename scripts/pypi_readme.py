"""Point the README's relative links at GitHub, for the package page on PyPI.

PyPI shows the README without the repository around it, so ``docs/usage.md``,
``LICENSE`` and the screenshot would not resolve there. The release workflow
runs this on its checkout before building; the README in the repository keeps
its relative links, which GitHub and the docs test follow.

    python -m scripts.pypi_readme v1.2.0     # links to the files at that tag
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def repository_url() -> str:
    """The GitHub repository named in pyproject.toml."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return project["urls"]["Repository"].rstrip("/")


def absolute_links(markdown: str, ref: str, repo: str) -> str:
    """Each relative link as a link to that file on GitHub at ``ref``; images as their raw file."""
    raw = repo.replace("https://github.com/", "https://raw.githubusercontent.com/", 1)

    def absolute(match: re.Match[str]) -> str:
        target = match.group(1)
        if re.match(r"[a-z]+:", target):  # https:, mailto:
            return match.group(0)
        if target.startswith("#"):  # a heading of this README: PyPI makes no heading anchors
            target = "README.md" + target
        path = target.split("#", 1)[0]
        base = f"{raw}/{ref}" if path.lower().endswith(IMAGE_SUFFIXES) else f"{repo}/blob/{ref}"
        return f"]({base}/{target})"

    return LINK_RE.sub(absolute, markdown)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.exit("usage: python -m scripts.pypi_readme <git tag, branch or commit>")
    README.write_text(absolute_links(README.read_text(encoding="utf-8"), args[0], repository_url()),
                      encoding="utf-8")
    print(f"Pointed the links in {README.name} at {repository_url()} ({args[0]})")


if __name__ == "__main__":
    main()
