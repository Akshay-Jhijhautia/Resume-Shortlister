"""The release notes of a version: its section of CHANGELOG.md, for the GitHub release.

    python -m scripts.release_notes 1.5.1 > notes.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
INSTALL = """
## Install or update

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main/install.ps1 | iex"
```

macOS or Linux (Terminal):

```bash
curl -LsSf https://raw.githubusercontent.com/Akshay-Jhijhautia/resume-shortlister/main/install.sh | sh
```

To try it without real resumes, download **resume-shortlister-sample-resumes.zip** below.
"""


def notes(version: str, changelog: str) -> str:
    """The changelog section headed ``## <version>`` (without the heading), then how to install."""
    match = re.search(rf"^## {re.escape(version)}\b.*?\n(.*?)(?=^## |\Z)", changelog, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"CHANGELOG.md has no section for {version}.")
    return match.group(1).strip() + "\n" + INSTALL


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.exit("usage: python -m scripts.release_notes <version>")
    print(notes(args[0].removeprefix("v"), CHANGELOG.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
